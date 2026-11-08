from httpx import AsyncClient

from tests.conftest import Env, FrozenClock
from tests.helpers import (
    ANIMATION_FOLDER,
    FILMS_FOLDER,
    INTAKE,
    add_heat,
    add_toy_story,
    automatic,
    decisions,
    seed_categories,
)
from tests.integration.test_scans import library, run_scan


async def test_undo_a_move_puts_the_movie_back_where_it_was(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (moved,) = await decisions(env)
    response = await owner.post(f"/api/v1/decisions/{moved.id}/revert")
    assert response.status_code == 200, response.text
    assert response.json()["target_root_folder"] == INTAKE
    await env.state.worker.tick()
    assert env.fakes.radarr is not None and env.fakes.radarr.library[1].root_folder_path == INTAKE
    # back in the intake folder, it is never sorted again on its own
    for _ in range(3):
        await env.state.worker.tick(poll=True)
    assert [d.status for d in await decisions(env)] == ["corrected", "moved"]


async def test_undoing_a_scan_move_returns_to_the_library_not_the_intake(owner: AsyncClient, env: Env):
    await seed_categories(env)
    library(env)
    scan = await run_scan(owner, env)
    await owner.post("/api/v1/decisions/apply-confident", json={"scan_id": scan["id"]})
    await env.state.worker.tick()
    assert env.fakes.radarr is not None and env.fakes.radarr.library[11].root_folder_path == ANIMATION_FOLDER
    moved = next(d for d in await decisions(env) if d.status == "moved")
    await owner.post(f"/api/v1/decisions/{moved.id}/revert")
    await env.state.worker.tick()
    assert env.fakes.radarr.library[11].root_folder_path == FILMS_FOLDER


async def test_undo_every_move_of_a_period_with_a_dry_run_first(
    owner: AsyncClient, env: Env, frozen_clock: FrozenClock
):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    first = frozen_clock()
    frozen_clock.advance(hours=2)
    since = frozen_clock().isoformat()
    add_heat(env)
    await env.state.worker.tick(poll=True)

    dry = await owner.post("/api/v1/decisions/revert", json={"since": since, "dry_run": True})
    assert dry.json()["count"] == 1
    assert [m["movie"]["title"] for m in dry.json()["items"]] == ["Heat"]
    assert env.fakes.radarr is not None and len(env.fakes.radarr.moves) == 2

    everything = await owner.post("/api/v1/decisions/revert", json={"dry_run": True})
    assert everything.json()["count"] == 2

    done = await owner.post("/api/v1/decisions/revert", json={"since": since})
    assert done.json()["count"] == 1
    await env.state.worker.tick()
    assert env.fakes.radarr.library[2].root_folder_path == INTAKE
    assert env.fakes.radarr.library[1].root_folder_path != INTAKE
    assert first < frozen_clock()


async def test_only_a_moved_movie_can_be_undone(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)  # preview: a proposal
    (proposal,) = await decisions(env)
    response = await owner.post(f"/api/v1/decisions/{proposal.id}/revert")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_moved"
