from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import Env
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
from triage.models import AuditEvent, MovieRef


async def _films_id(owner: AsyncClient) -> int:
    return next(c["id"] for c in (await owner.get("/api/v1/categories")).json() if c["key"] == "films")


async def test_correct_to_another_category(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (moved,) = await decisions(env)
    response = await owner.post(
        f"/api/v1/decisions/{moved.id}/correct", json={"category_id": await _films_id(owner)}
    )
    assert response.status_code == 200
    await env.state.worker.tick()

    original, correction = await decisions(env)
    assert original.status == "corrected"
    assert (correction.source, correction.actor, correction.status) == ("correction", "owner", "moved")
    assert env.fakes.radarr is not None and env.fakes.radarr.library[1].root_folder_path == FILMS_FOLDER
    async with env.state.session_factory() as db:
        ref = await db.get(MovieRef, 1)
        assert ref is not None and ref.corrected
        actions = [e.action for e in await db.scalars(select(AuditEvent).order_by(AuditEvent.id))]
    assert actions == ["move", "move"]


async def test_back_to_intake_is_never_sorted_again(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (moved,) = await decisions(env)
    await owner.post(f"/api/v1/decisions/{moved.id}/correct", json={"target": "intake"})
    await env.state.worker.tick()
    assert env.fakes.radarr is not None and env.fakes.radarr.library[1].root_folder_path == INTAKE
    for _ in range(3):
        await env.state.worker.tick(poll=True)
    statuses = [d.status for d in await decisions(env)]
    assert statuses == ["corrected", "moved"]
    assert len(env.fakes.radarr.moves) == 2


async def _in_place(owner: AsyncClient, env: Env, folder: str, title: str) -> dict:
    scan = await run_scan(owner, env, folder)
    found = (await owner.get(f"/api/v1/scans/{scan['id']}/page?tab=in_place")).json()["items"]
    return next(d for d in found if d["movie"]["title"] == title)


async def _category_id(owner: AsyncClient, key: str) -> int:
    return next(c["id"] for c in (await owner.get("/api/v1/categories")).json() if c["key"] == key)


async def test_a_movie_already_in_place_can_be_moved_by_hand(owner: AsyncClient, env: Env):
    """A check found it in the right library; the owner still wants it elsewhere."""
    await seed_categories(env)
    library(env)
    heat = await _in_place(owner, env, FILMS_FOLDER, "Heat")
    animation = await _category_id(owner, "animation")
    response = await owner.post(f"/api/v1/decisions/{heat['id']}/correct", json={"category_id": animation})
    assert response.status_code == 200, response.text
    assert response.json()["from_root_folder"] == FILMS_FOLDER
    await env.state.worker.tick()

    assert env.fakes.radarr is not None and env.fakes.radarr.library[10].root_folder_path == ANIMATION_FOLDER
    assert (await owner.get(f"/api/v1/decisions/{heat['id']}")).json()["status"] == "corrected"
    sheet = (await owner.get(f"/api/v1/decisions/{response.json()['id']}")).json()
    assert (sheet["status"], sheet["movie"]["lock"]["folder"]) == ("moved", ANIMATION_FOLDER)


async def test_a_locked_movie_in_place_moves_from_where_it_is(owner: AsyncClient, env: Env):
    """Locked in a library its rules would not choose: in place there, and moved from there."""
    await seed_categories(env)
    library(env)
    heat = await _in_place(owner, env, FILMS_FOLDER, "Heat")
    animation = await _category_id(owner, "animation")
    await owner.post(f"/api/v1/decisions/{heat['id']}/correct", json={"category_id": animation})
    await env.state.worker.tick()

    locked = await _in_place(owner, env, ANIMATION_FOLDER, "Heat")
    assert locked["target_root_folder"] == FILMS_FOLDER  # today's rules
    response = await owner.post(
        f"/api/v1/decisions/{locked['id']}/correct", json={"category_id": await _films_id(owner)}
    )
    assert response.json()["from_root_folder"] == ANIMATION_FOLDER
    await env.state.worker.tick()
    assert env.fakes.radarr is not None and env.fakes.radarr.library[10].root_folder_path == FILMS_FOLDER


async def test_only_moves_can_be_corrected(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)  # preview: a proposal
    (proposal,) = await decisions(env)
    response = await owner.post(f"/api/v1/decisions/{proposal.id}/correct", json={"target": "intake"})
    assert response.status_code == 409


async def test_history_filters(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    all_items = (await owner.get("/api/v1/decisions")).json()["items"]
    assert len(all_items) == 2
    toy = (await owner.get("/api/v1/decisions", params={"q": "toy"})).json()["items"]
    assert [d["movie"]["title"] for d in toy] == ["Toy Story"]
    films = (await owner.get("/api/v1/decisions", params={"category": await _films_id(owner)})).json()[
        "items"
    ]
    assert [d["movie"]["title"] for d in films] == ["Heat"]
    page = (await owner.get("/api/v1/decisions", params={"limit": 1})).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    rest = (await owner.get("/api/v1/decisions", params={"limit": 1, "cursor": page["next_cursor"]})).json()
    assert len(rest["items"]) == 1 and rest["next_cursor"] is None
