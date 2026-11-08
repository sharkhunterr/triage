from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import Env
from tests.helpers import (
    ANIMATION_FOLDER,
    FILMS_FOLDER,
    add_heat,
    add_toy_story,
    arrivals,
    automatic,
    decisions,
    seed_categories,
    work_items,
)
from triage.models import AuditEvent


async def test_a_clearly_animated_movie_is_moved_to_its_library(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)

    assert env.fakes.radarr is not None
    assert env.fakes.radarr.moves == [
        {"movieIds": [1], "rootFolderPath": ANIMATION_FOLDER, "deleteFiles": False}
    ]
    assert env.fakes.radarr.library[1].root_folder_path == ANIMATION_FOLDER
    (decision,) = await decisions(env)
    assert (decision.status, decision.actor, decision.target_root_folder) == (
        "moved",
        "triage",
        ANIMATION_FOLDER,
    )
    assert decision.confidence >= 0.8
    (arrival,) = await arrivals(env)
    assert arrival.close_reason == "moved_by_triage"
    async with env.state.session_factory() as db:
        (event,) = await db.scalars(select(AuditEvent))
        assert (event.action, event.from_path, event.to_path) == ("move", "/media/intake", ANIMATION_FOLDER)


async def test_a_live_action_movie_goes_to_the_fallback(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert (decision.status, decision.target_root_folder) == ("moved", FILMS_FOLDER)


async def test_preview_mode_only_proposes(env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert (decision.status, decision.target_root_folder) == ("proposed", ANIMATION_FOLDER)
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_radarr_down_at_move_time_is_retried(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.fail_moves = True
    await env.state.worker.tick(poll=True)
    (move,) = await work_items(env, "move")
    assert (move.state, move.attempts, move.last_error) == ("pending", 1, "Radarr: answered HTTP 503")
    (decision,) = await decisions(env)
    assert decision.status == "moving"

    env.fakes.radarr.fail_moves = False
    env.clock.advance(minutes=2)
    await env.state.worker.drain()
    (decision,) = await decisions(env)
    assert decision.status == "moved"


async def test_an_unconfirmed_move_ends_failed_after_retries(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.ignore_moves = True
    await env.state.worker.tick(poll=True)
    for _ in range(10):
        env.clock.advance(hours=1)
        await env.state.worker.drain()
    (decision,) = await decisions(env)
    assert decision.status == "failed"
    assert "did not move" in (decision.error or "")


async def test_a_category_without_library_holds_the_movie(env: Env):
    await seed_categories(env, animation_folder=None)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert {"code": "category_without_folder", "category": "animation"} in decision.reasons


async def test_no_category_holds_the_movie(env: Env):
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert decision.reasons == [{"code": "no_categories"}]


async def test_tmdb_down_retries_the_classification(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    assert env.fakes.tmdb is not None
    env.fakes.tmdb.down = True
    await env.state.worker.tick(poll=True)
    assert await decisions(env) == []
    (classify,) = await work_items(env, "classify")
    assert (classify.state, classify.attempts) == ("pending", 1)
    env.fakes.tmdb.down = False
    env.clock.advance(minutes=2)
    await env.state.worker.drain()
    (decision,) = await decisions(env)
    assert decision.status == "moved"


async def test_without_tmdb_radarr_metadata_is_enough(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_heat(env)
    env.fakes.tmdb = None
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved"


async def test_decision_detail_separates_facts_from_ai(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    detail = (await owner.get(f"/api/v1/decisions/{decision.id}")).json()
    assert detail["movie"]["title"] == "Toy Story"
    assert {s["kind"] for s in detail["signals"]} == {"fact"}
    assert detail["ai"] is None
    assert detail["facts"]["company"] == ["Pixar"]
    assert detail["top_category"]["key"] == "animation"
    assert detail["categories"][0]["name"] == "Dessins animés"

    listing = (await owner.get("/api/v1/decisions", params={"status": "proposed"})).json()
    assert [d["id"] for d in listing["items"]] == [decision.id]
    dashboard = (await owner.get("/api/v1/dashboard")).json()
    assert dashboard["counts"]["proposed"] == 1
    assert dashboard["mode"] == "preview"
    assert dashboard["latest"][0]["movie"]["title"] == "Toy Story"
