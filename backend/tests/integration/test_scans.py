from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import (
    ANIMATION_FOLDER,
    FILMS_FOLDER,
    INTAKE,
    add_toy_story,
    automatic,
    decisions,
    seed_categories,
)


def library(env: Env) -> None:
    """Films library: one live-action movie in place, one misplaced animated movie."""
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    env.fakes.radarr.add(10, "Heat", folder=FILMS_FOLDER, genres=["Crime"], tmdb_id=949)
    env.fakes.radarr.add(
        11, "Spirited Away", folder=FILMS_FOLDER, genres=["Animation", "Fantasy"], tmdb_id=129
    )
    env.fakes.tmdb.set(129, genres=["Animation"], companies=["Studio Ghibli", "Pixar"])
    env.fakes.radarr.add(12, "Elsewhere", folder=ANIMATION_FOLDER, genres=["Animation"])


async def run_scan(owner: AsyncClient, env: Env, folder: str = FILMS_FOLDER) -> dict:
    response = await owner.post("/api/v1/scans", json={"root_folder_path": folder})
    assert response.status_code == 202, response.text
    await env.state.worker.tick()
    return (await owner.get(f"/api/v1/scans/{response.json()['id']}")).json()


async def test_a_scan_proposes_and_never_moves(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)  # even in automatic mode, a scan only proposes
    library(env)
    scan = await run_scan(owner, env)
    assert (scan["state"], scan["total"], scan["done"]) == ("done", 2, 2)

    results = (await owner.get(f"/api/v1/scans/{scan['id']}/results")).json()
    by_title = {r["movie"]["title"]: r for r in results}
    assert set(by_title) == {"Heat", "Spirited Away"}
    assert by_title["Heat"]["status"] == "in_place"
    assert by_title["Spirited Away"]["status"] == "proposed"
    assert by_title["Spirited Away"]["target_root_folder"] == ANIMATION_FOLDER
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_apply_confident_is_limited_to_the_scan(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    add_toy_story(env)  # an intake proposal outside the scan
    await env.state.worker.tick(poll=True)
    scan = await run_scan(owner, env)
    response = await owner.post("/api/v1/decisions/apply-confident", json={"scan_id": scan["id"]})
    assert response.json() == {"applied": 1}
    await env.state.worker.tick()
    assert env.fakes.radarr is not None
    assert env.fakes.radarr.library[11].root_folder_path == ANIMATION_FOLDER
    assert env.fakes.radarr.library[1].root_folder_path == INTAKE


async def test_one_scan_at_a_time_and_folders_are_checked(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    first = await owner.post("/api/v1/scans", json={"root_folder_path": FILMS_FOLDER})
    assert first.status_code == 202
    second = await owner.post("/api/v1/scans", json={"root_folder_path": INTAKE})
    assert second.status_code == 409
    await env.state.worker.tick()
    unknown = await owner.post("/api/v1/scans", json={"root_folder_path": "/nowhere"})
    assert unknown.status_code == 422


async def test_cancel_keeps_partial_results(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    started = (await owner.post("/api/v1/scans", json={"root_folder_path": FILMS_FOLDER})).json()
    worker = env.state.worker
    async with env.state.session_factory() as db:
        from triage.worker import queue

        start = await queue.claim_next(db)
        await db.commit()
    assert start is not None
    await worker._process(start.id)  # list the movies: two scan_movie items queued
    async with env.state.session_factory() as db:
        first = await queue.claim_next(db)
        await db.commit()
    assert first is not None
    await worker._process(first.id)  # one movie classified
    cancelled = await owner.post(f"/api/v1/scans/{started['id']}/cancel")
    assert cancelled.json()["state"] == "cancelled"
    await worker.tick()
    scan = (await owner.get(f"/api/v1/scans/{started['id']}")).json()
    assert (scan["state"], scan["done"]) == ("cancelled", 1)
    assert len((await owner.get(f"/api/v1/scans/{started['id']}/results")).json()) == 1


async def test_a_movie_already_pending_is_not_classified_twice(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)  # intake proposal
    await run_scan(owner, env, INTAKE)
    assert len([d for d in await decisions(env) if d.radarr_id == 1]) == 1


async def test_scans_are_listed_newest_first(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    a = await run_scan(owner, env)
    b = await run_scan(owner, env, ANIMATION_FOLDER)
    assert [s["id"] for s in (await owner.get("/api/v1/scans")).json()] == [b["id"], a["id"]]
