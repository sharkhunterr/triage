import asyncio

from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import Env
from tests.helpers import FILMS_FOLDER, add_heat, add_toy_story, seed_categories
from triage.core.settings import load_settings
from triage.models import Scan, WorkItem
from triage.worker import queue
from triage.worker.runner import JobContext


async def poll_only(env: Env) -> None:
    """New movies are found and queued, none analysed yet."""
    async with env.state.session_factory() as db:
        settings = await load_settings(db)
    await env.state.worker.poll(settings)


async def states(env: Env, kind: str) -> list[str]:
    async with env.state.session_factory() as db:
        return [i.state for i in await db.scalars(select(WorkItem).where(WorkItem.kind == kind))]


async def test_the_activity_lists_what_waits_and_queued_analyses_stop(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    add_heat(env)
    await poll_only(env)

    queued = (await owner.get("/api/v1/activity")).json()["queue"]
    assert queued == [{"kind": "classify", "scan_id": None, "folder": None, "count": 2, "stoppable": True}]

    response = await owner.post("/api/v1/activity/stop", json={"kind": "classify"})
    assert response.status_code == 200 and response.json() == {"stopped": 2}
    assert await states(env, "classify") == ["cancelled", "cancelled"]
    activity = (await owner.get("/api/v1/activity")).json()
    assert activity["queue"] == [] and (activity["run"] is None or activity["run"]["pending"] == 0)

    # nothing analysed, nothing moved: both are new movies to analyse again later
    await env.state.worker.tick()
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []
    counts = (await owner.post("/api/v1/decisions/reanalyze", json={"dry_run": True})).json()
    assert counts["new"] == 2


async def test_a_check_stops_with_its_queued_movies(owner: AsyncClient, env: Env):
    await seed_categories(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.add(10, "Heat", folder=FILMS_FOLDER, genres=["Crime"], tmdb_id=949)
    env.fakes.radarr.add(11, "Ronin", folder=FILMS_FOLDER, genres=["Action"])
    scan_id = (await owner.post("/api/v1/scans", json={"root_folder_path": FILMS_FOLDER})).json()["id"]
    async with env.state.session_factory() as db:  # the check lists its movies, none analysed yet
        start = await queue.claim_next(db)
        await db.commit()
    assert start is not None and start.kind == "scan_start"
    await env.state.worker._process(start.id)

    queued = (await owner.get("/api/v1/activity")).json()["queue"]
    assert queued == [
        {"kind": "scan", "scan_id": scan_id, "folder": FILMS_FOLDER, "count": 2, "stoppable": True}
    ]
    response = await owner.post("/api/v1/activity/stop", json={"kind": "scan", "scan_id": scan_id})
    assert response.json() == {"stopped": 2}
    assert await states(env, "scan_movie") == ["cancelled", "cancelled"]
    async with env.state.session_factory() as db:
        scan = await db.get(Scan, scan_id)
        assert scan is not None and scan.state == "cancelled" and scan.finished_at is not None


async def test_the_running_analysis_is_interrupted(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await poll_only(env)
    started, never = asyncio.Event(), asyncio.Event()

    async def slow(_ctx: JobContext, _item: WorkItem) -> None:
        started.set()
        await never.wait()  # an AI that never answers

    env.state.worker.handlers["classify"] = slow
    drain = asyncio.create_task(env.state.worker.drain())
    await asyncio.wait_for(started.wait(), 2)
    running = (await owner.get("/api/v1/activity")).json()["running"]
    assert running["kind"] == "classify" and running["stoppable"] is True

    response = await owner.post("/api/v1/activity/stop", json={"kind": "classify"})
    assert response.json() == {"stopped": 1}
    await asyncio.wait_for(drain, 2)
    assert await states(env, "classify") == ["cancelled"]
    activity = (await owner.get("/api/v1/activity")).json()
    assert activity["running"] is None
    assert activity["recent"][0]["outcome"] == "stopped" and activity["recent"][0]["error"] is None


async def test_everything_stoppable_stops_at_once_but_moves_go_through(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await poll_only(env)
    async with env.state.session_factory() as db:
        await queue.enqueue(db, "refresh_titles", {})
        await queue.enqueue(db, "move", {"decision_id": 999})
        await db.commit()

    queued = {g["kind"]: g for g in (await owner.get("/api/v1/activity")).json()["queue"]}
    assert queued["move"]["stoppable"] is False
    assert (await owner.post("/api/v1/activity/stop", json={"kind": "move"})).status_code == 422

    response = await owner.post("/api/v1/activity/stop", json={"kind": "all"})
    assert response.json() == {"stopped": 2}
    assert await states(env, "move") == ["pending"]
    assert [g["kind"] for g in (await owner.get("/api/v1/activity")).json()["queue"]] == ["move"]
