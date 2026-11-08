from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import (
    ANIMATION_FOLDER,
    FILMS_FOLDER,
    add_ambiguous,
    add_heat,
    add_toy_story,
    automatic,
    decisions,
    seed_categories,
)


async def test_preview_is_the_default_and_only_proposes(env: Env):
    await seed_categories(env)
    add_toy_story(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    assert {d.status for d in await decisions(env)} == {"proposed"}
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_apply_one_proposal_moves_only_that_movie(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    toy, heat = await decisions(env)
    response = await owner.post(
        f"/api/v1/decisions/{toy.id}/apply", json={"category_id": toy.target_category_id}
    )
    assert response.status_code == 200
    await env.state.worker.tick()
    assert env.fakes.radarr is not None
    assert [m["rootFolderPath"] for m in env.fakes.radarr.moves] == [ANIMATION_FOLDER]
    toy, heat = await decisions(env)
    assert (toy.status, toy.actor, heat.status) == ("moved", "owner", "proposed")


async def test_pick_another_category_for_a_proposal(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (toy,) = await decisions(env)
    films = next(c for c in (await owner.get("/api/v1/categories")).json() if c["key"] == "films")
    await owner.post(f"/api/v1/decisions/{toy.id}/apply", json={"category_id": films["id"]})
    await env.state.worker.tick()
    (toy,) = await decisions(env)
    assert (toy.status, toy.target_root_folder) == ("moved", FILMS_FOLDER)


async def test_dismiss_a_proposal(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (toy,) = await decisions(env)
    assert (await owner.post(f"/api/v1/decisions/{toy.id}/dismiss")).status_code == 200
    (toy,) = await decisions(env)
    assert (toy.status, toy.actor) == ("dismissed", "owner")
    assert (await owner.post(f"/api/v1/decisions/{toy.id}/dismiss")).status_code == 409


async def test_apply_all_confident_proposals(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    add_heat(env)
    add_ambiguous(env)  # held, not a proposal
    await env.state.worker.tick(poll=True)
    response = await owner.post("/api/v1/decisions/apply-confident", json={})
    assert response.json() == {"applied": 2}
    await env.state.worker.tick()
    statuses = {d.radarr_id: d.status for d in await decisions(env)}
    assert statuses == {1: "moved", 2: "moved", 3: "held"}


async def test_switching_to_automatic_leaves_pending_proposals(env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    await automatic(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    statuses = {d.radarr_id: d.status for d in await decisions(env)}
    assert statuses == {1: "proposed", 2: "moved"}
