import re

from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import (
    ANIMATION_FOLDER,
    add_ambiguous,
    arrivals,
    automatic,
    decisions,
    seed_categories,
)

SMTP = {"host": "smtp.test", "sender": "triage@example.org", "recipient": "owner@example.org"}


async def held_movie_link(env: Env) -> str:
    await seed_categories(env)
    await automatic(env)
    await env.settings(smtp=SMTP)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    assert env.fakes.mailer is not None
    (message,) = env.fakes.mailer.sent
    match = re.search(r"http://triage\.test(/r/[\w-]+)", message.text)
    assert match
    return match.group(1)


async def test_opening_a_link_only_shows_a_confirmation(client: AsyncClient, env: Env):
    path = await held_movie_link(env)
    page = await client.get(path, params={"c": "animation"})
    assert page.status_code == 200
    assert "Perfect Blue" in page.text and "Dessins animés" in page.text
    assert '<form method="post"' in page.text
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_confirming_moves_the_movie_once(client: AsyncClient, env: Env):
    path = await held_movie_link(env)
    done = await client.post(path, data={"c": "animation"})
    assert done.status_code == 200
    await env.state.worker.tick()
    (decision,) = await decisions(env)
    assert (decision.status, decision.actor, decision.target_root_folder) == (
        "moved",
        "owner",
        ANIMATION_FOLDER,
    )
    again = await client.post(path, data={"c": "films"})
    assert again.status_code == 410
    assert "/review" in again.text


async def test_links_expire(client: AsyncClient, env: Env):
    path = await held_movie_link(env)
    env.clock.advance(days=8)
    assert (await client.post(path, data={"c": "animation"})).status_code == 410


async def test_deciding_in_the_app_revokes_the_links(owner: AsyncClient, env: Env):
    path = await held_movie_link(env)
    (decision,) = await decisions(env)
    categories = (await owner.get("/api/v1/categories")).json()
    films = next(c for c in categories if c["key"] == "films")
    response = await owner.post(f"/api/v1/decisions/{decision.id}/apply", json={"category_id": films["id"]})
    assert response.status_code == 200
    assert (await owner.post(path, data={"c": "animation"})).status_code == 410


async def test_leave_in_intake_is_final_for_this_arrival(client: AsyncClient, env: Env):
    path = await held_movie_link(env)
    assert (await client.post(path, data={"c": "intake"})).status_code == 200
    (decision,) = await decisions(env)
    assert decision.status == "left_in_intake"
    await env.state.worker.tick(poll=True)
    assert len(await decisions(env)) == 1
    (arrival,) = await arrivals(env)
    assert arrival.closed_at is None
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_unknown_choice_or_token(client: AsyncClient, env: Env):
    path = await held_movie_link(env)
    assert (await client.post(path, data={"c": "documentaries"})).status_code == 400
    assert (await client.get("/r/not-a-token", params={"c": "animation"})).status_code == 410


async def test_review_queue_and_apply_from_the_app(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    (item,) = (await owner.get("/api/v1/review")).json()
    assert item["status"] == "held"
    assert (await owner.get("/api/v1/review/count")).json() == {"review": 1}

    animation = next(c for c in (await owner.get("/api/v1/categories")).json() if c["key"] == "animation")
    applied = await owner.post(f"/api/v1/decisions/{item['id']}/apply", json={"category_id": animation["id"]})
    assert applied.json()["status"] == "moving"
    await env.state.worker.tick()
    (decision,) = await decisions(env)
    assert decision.status == "moved"
    assert (await owner.get("/api/v1/review/count")).json() == {"review": 0}


async def test_apply_refuses_finished_decisions(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    await owner.post(f"/api/v1/decisions/{decision.id}/apply", json={"target": "intake"})
    response = await owner.post(f"/api/v1/decisions/{decision.id}/apply", json={"target": "intake"})
    assert response.status_code == 409
