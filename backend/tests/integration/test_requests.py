from httpx import AsyncClient

from tests.conftest import Env
from tests.fakes.seerr import FakeSeerr
from tests.helpers import add_toy_story, automatic, decisions, seed_categories, work_items


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
