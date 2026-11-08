from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import (
    ANIMATION_FOLDER,
    add_ambiguous,
    add_heat,
    add_toy_story,
    automatic,
    decisions,
    seed_categories,
)
from triage.models import Category, Rule


async def _animation_id(owner: AsyncClient) -> int:
    return next(c["id"] for c in (await owner.get("/api/v1/categories")).json() if c["key"] == "animation")


async def test_reanalyze_classifies_every_waiting_movie_again_with_todays_rules(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_ambiguous(env)  # held: Animation alone is not enough
    await env.state.worker.tick(poll=True)
    assert [d.status for d in await decisions(env)] == ["held"]

    async with env.state.session_factory() as db:
        category = await db.get(Category, await _animation_id(owner))
        assert category is not None
        category.rules.append(Rule(field="company", operator="contains", value="Madhouse", weight=40))
        await db.commit()

    dry = await owner.post("/api/v1/decisions/reanalyze", json={"dry_run": True})
    assert dry.json() == {"count": 1, "all": 1, "waiting": 1, "new": 0}
    assert [d.status for d in await decisions(env)] == ["held"]

    done = await owner.post("/api/v1/decisions/reanalyze", json={})
    assert done.json()["count"] == 1
    await env.state.worker.tick()
    assert [d.status for d in await decisions(env)] == ["superseded", "proposed"]


async def test_decide_several_movies_at_once(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)  # proposal: animation
    add_heat(env)  # proposal: films
    add_ambiguous(env)  # held
    await env.state.worker.tick(poll=True)
    toy, heat, blue = await decisions(env)
    assert (toy.status, heat.status, blue.status) == ("proposed", "proposed", "held")

    response = await owner.post(
        "/api/v1/decisions/bulk",
        json={
            "items": [
                {"id": toy.id, "category_id": await _animation_id(owner)},
                {"id": heat.id, "target": "intake"},
            ]
        },
    )
    assert response.json() == {"applied": 2, "failed": []}
    await env.state.worker.tick()
    toy, heat, blue = await decisions(env)
    assert (toy.status, heat.status, blue.status) == ("moved", "dismissed", "held")
    assert env.fakes.radarr is not None and env.fakes.radarr.library[1].root_folder_path == ANIMATION_FOLDER


async def test_a_bulk_item_that_cannot_be_applied_is_reported_not_fatal(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    add_heat(env)
    await env.state.worker.tick(poll=True)
    toy, heat = await decisions(env)
    response = await owner.post(
        "/api/v1/decisions/bulk",
        json={"items": [{"id": toy.id, "category_id": 999}, {"id": heat.id, "target": "intake"}]},
    )
    assert response.json() == {"applied": 1, "failed": [toy.id]}


async def test_reanalyze_also_takes_the_movies_put_back_in_the_intake_folder(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (moved,) = await decisions(env)
    # an earlier "back to the intake folder" correction: that stay counted as decided
    await owner.post(f"/api/v1/decisions/{moved.id}/correct", json={"target": "intake"})
    await env.state.worker.tick(poll=True)
    assert [d.status for d in await decisions(env)] == ["corrected", "moved"]

    assert (await owner.post("/api/v1/decisions/reanalyze", json={"dry_run": True})).json()["count"] == 1
    await owner.post("/api/v1/decisions/reanalyze", json={})
    await env.state.worker.tick()
    assert [d.status for d in await decisions(env)] == ["corrected", "moved", "proposed"]


async def test_analyze_only_the_new_ones(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)
    (moved,) = await decisions(env)
    await owner.post(f"/api/v1/decisions/{moved.id}/correct", json={"target": "intake"})  # put back
    add_ambiguous(env)  # held: waiting for a decision
    await env.state.worker.tick(poll=True)

    counts = (await owner.post("/api/v1/decisions/reanalyze", json={"scope": "new", "dry_run": True})).json()
    assert counts == {"count": 1, "all": 2, "waiting": 1, "new": 1}
    await owner.post("/api/v1/decisions/reanalyze", json={"scope": "new"})
    await env.state.worker.tick()
    statuses = sorted(d.status for d in await decisions(env))
    assert statuses == ["corrected", "held", "moved", "proposed"]  # the held one was left alone
