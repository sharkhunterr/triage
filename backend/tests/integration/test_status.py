from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import add_toy_story, automatic, seed_categories, work_items
from triage.adapters.types import RootFolder
from triage.models import Category


async def test_status_reports_each_service(owner: AsyncClient, env: Env):
    status = (await owner.get("/api/v1/status")).json()
    services = status["services"]
    assert services["radarr"]["state"] == "ok"
    assert services["tmdb"]["state"] == "ok"
    assert services["ollama"]["state"] == "disabled"
    assert services["seerr"]["state"] == "disabled"
    assert services["smtp"]["state"] == "ok"
    assert status["mode"] == "preview"


async def test_a_down_service_and_failed_items(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.ignore_moves = True
    await env.state.worker.tick(poll=True)
    for _ in range(10):
        env.clock.advance(hours=1)
        await env.state.worker.drain()
    env.fakes.radarr.down = True
    env.clock.advance(minutes=5)  # health is cached one minute
    status = (await owner.get("/api/v1/status")).json()
    assert status["services"]["radarr"]["state"] == "down"
    (failed,) = status["failed_items"]
    assert failed["kind"] == "move" and "did not move" in failed["last_error"]

    env.fakes.radarr.down = False
    env.fakes.radarr.ignore_moves = False
    assert (await owner.post(f"/api/v1/work-items/{failed['id']}/retry")).status_code == 204
    (move,) = await work_items(env, "move")
    assert (move.state, move.attempts) == ("pending", 0)


async def test_category_library_warnings(owner: AsyncClient, env: Env):
    await seed_categories(env)
    async with env.state.session_factory() as db:
        db.add(Category(key="gone", name="Gone", root_folder_path="/media/gone", position=9, version=1))
        await db.commit()
    assert env.fakes.radarr is not None
    env.fakes.radarr.folders = [
        RootFolder("/media/intake"),
        RootFolder("/media/films"),
        RootFolder("/media/animation", accessible=False),
    ]
    warnings = (await owner.get("/api/v1/status")).json()["folder_warnings"]
    assert {(w["category"], w["problem"]) for w in warnings} == {
        ("Gone", "missing"),
        ("Dessins animés", "inaccessible"),
    }


async def test_check_now_triggers_a_poll(owner: AsyncClient, env: Env):
    response = await owner.post("/api/v1/poll")
    assert response.status_code == 204
    assert env.state.worker.next_poll_at is not None
