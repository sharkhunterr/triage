from dataclasses import replace
from datetime import UTC, datetime

from httpx import AsyncClient

from tests.conftest import Env
from tests.fakes.seerr import FakeSeerr
from tests.helpers import add_heat, add_toy_story, automatic, decisions, seed_categories, work_items
from triage.models import MovieRef


async def test_a_moved_request_is_verified_and_shown(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    env.fakes.seerr = FakeSeerr()
    env.fakes.seerr.add(41, 862, requested_by="Alice")
    await env.state.worker.tick(poll=True)

    (decision,) = await decisions(env)
    assert decision.status == "moved"
    assert decision.request_check is not None
    assert decision.request_check["tracked"] is True
    assert (decision.request_check["request_id"], decision.request_check["requester"]) == (41, "Alice")
    detail = (await owner.get(f"/api/v1/decisions/{decision.id}")).json()
    assert detail["request_check"]["requester"] == "Alice"


async def test_seerr_down_retries_and_keeps_the_move(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    env.fakes.seerr = FakeSeerr()
    env.fakes.seerr.down = True
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved" and decision.request_check is None
    (verify,) = await work_items(env, "verify_request")
    assert verify.state == "pending" and verify.attempts == 1
    env.fakes.seerr.down = False
    env.fakes.seerr.add(41, 862)
    env.clock.advance(minutes=2)
    await env.state.worker.drain()
    (decision,) = await decisions(env)
    assert decision.request_check is not None and decision.request_check["tracked"]


async def test_a_movie_without_request_is_noted(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    env.fakes.seerr = FakeSeerr()
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.request_check == {
        "tracked": False,
        "request_id": None,
        "requester": None,
        "status": None,
        "requested_at": None,
        "checked_at": env.clock.current.isoformat(),
    }


async def test_nothing_is_ever_written_to_seerr_or_recreated_in_radarr(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    env.fakes.seerr = FakeSeerr()
    env.fakes.seerr.add(41, 862)
    await env.state.worker.tick(poll=True)
    assert env.fakes.radarr is not None
    assert {call for call, _ in env.fakes.radarr.calls} <= {"movies", "movie", "move", "root_folders"}
    assert not hasattr(env.fakes.seerr, "update")


async def test_each_movie_tells_who_asked_for_it_and_when(owner: AsyncClient, env: Env):
    """Seerr's requests read in one pass after a poll: each movie says who asked for it and when, and
    when Radarr added it; a movie no one requested is looked up once all the same."""
    await seed_categories(env)
    asked = datetime(2026, 11, 7, 18, 30, tzinfo=UTC)
    added = datetime(2026, 11, 7, 18, 31, tzinfo=UTC)
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    add_toy_story(env)
    env.fakes.radarr.library[1] = replace(env.fakes.radarr.library[1], added=added)
    add_heat(env)
    env.fakes.seerr = FakeSeerr()
    env.fakes.seerr.add(41, 862, requested_by="Alice", requested_at=asked)
    await env.state.worker.tick(poll=True)
    await env.state.worker.drain()

    movies = {d["movie"]["title"]: d["movie"] for d in (await owner.get("/api/v1/review")).json()}
    toy = movies["Toy Story"]
    assert toy["requested_by"] == "Alice"
    assert toy["requested_at"].startswith("2026-11-07T18:30")
    assert toy["added_at"].startswith("2026-11-07T18:31")
    assert movies["Heat"]["requested_by"] is None  # no request: nothing invented
    assert env.fakes.seerr.sweeps == 1

    env.fakes.radarr.library[2] = replace(
        env.fakes.radarr.library[2], added=added, root_folder_path="/elsewhere"
    )
    await env.state.worker.tick(poll=True)
    await env.state.worker.drain()
    assert env.fakes.seerr.sweeps == 1  # every movie looked up: Seerr is not asked again
    async with env.state.session_factory() as db:
        heat_ref = await db.get(MovieRef, 2)
        assert heat_ref is not None and heat_ref.added_at == added  # out of the intake, still told
