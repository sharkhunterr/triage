from dataclasses import replace

from tests.conftest import Env
from tests.helpers import FILMS_FOLDER, INTAKE, add_heat, add_toy_story, arrivals, decisions, seed_categories
from triage.worker.jobs import build_worker


async def test_a_new_intake_movie_gets_one_arrival_and_one_decision(env: Env):
    await seed_categories(env)
    add_toy_story(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.add(9, "Already sorted", folder=FILMS_FOLDER, genres=["Drama"])
    await env.state.worker.tick(poll=True)

    (arrival,) = await arrivals(env)
    assert (arrival.radarr_id, arrival.intake_path, arrival.closed_at) == (1, INTAKE, None)
    (decision,) = await decisions(env)
    assert decision.radarr_id == 1 and decision.arrival_id == arrival.id
    assert 9 not in {d.radarr_id for d in await decisions(env)}


async def test_repeated_polls_and_restarts_do_not_duplicate(env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    await env.state.worker.tick(poll=True)
    restarted = build_worker(env.state.session_factory, env.state.adapter_factory)
    await restarted.tick(poll=True)
    assert len(await arrivals(env)) == 1
    assert len(await decisions(env)) == 1


async def test_a_movie_moved_by_hand_closes_its_arrival_and_supersedes_the_proposal(env: Env):
    await seed_categories(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)  # preview mode: a proposal
    (decision,) = await decisions(env)
    assert decision.status == "proposed"

    assert env.fakes.radarr is not None
    env.fakes.radarr.library[2] = replace(env.fakes.radarr.library[2], root_folder_path=FILMS_FOLDER)
    await env.state.worker.tick(poll=True)

    (arrival,) = await arrivals(env)
    assert arrival.closed_at is not None and arrival.close_reason == "moved_elsewhere"
    (decision,) = await decisions(env)
    assert decision.status == "superseded"
    assert env.fakes.radarr.moves == []


async def test_a_movie_removed_from_radarr_closes_its_arrival(env: Env):
    await seed_categories(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    assert env.fakes.radarr is not None
    del env.fakes.radarr.library[2]
    await env.state.worker.tick(poll=True)
    (arrival,) = await arrivals(env)
    assert arrival.close_reason == "removed_from_radarr"


async def test_radarr_down_is_reported_without_crashing(env: Env):
    assert env.fakes.radarr is not None
    env.fakes.radarr.down = True
    await env.state.worker.tick(poll=True)
    assert env.state.worker.last_poll_error == "unreachable (ConnectError)"
    assert await arrivals(env) == []


async def test_nothing_happens_without_intake_folders(env: Env):
    await env.settings(radarr={"intake_root_folders": []})
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    assert await arrivals(env) == []
