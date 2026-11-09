"""The review queue a page at a time: each tab paged in the order movies arrived, the counts of both tabs,
a page past the end giving the last one."""

from datetime import timedelta

from httpx import AsyncClient

from tests.conftest import Env
from triage.domain import decisions as d
from triage.models import Decision, MovieRef


async def _waiting(env: Env, held: int, proposed: int) -> None:
    async with env.state.session_factory() as db:
        for n in range(held + proposed):
            db.add(
                MovieRef(radarr_id=n + 1, tmdb_id=n + 1, title=f"Movie {n + 1}", updated_at=env.clock.current)
            )
        await db.flush()
        for n in range(held + proposed):
            db.add(
                Decision(
                    radarr_id=n + 1,
                    source="intake",
                    signals=[],
                    scores={},
                    reasons=[],
                    categories_snapshot=[],
                    status=d.HELD if n < held else d.PROPOSED,
                    confidence=0.85 if n % 2 else 0.0,
                    created_at=env.clock.current + timedelta(minutes=n),
                )
            )
        await db.commit()


async def test_the_review_queue_comes_a_page_at_a_time(owner: AsyncClient, env: Env):
    await _waiting(env, held=2, proposed=7)
    first = (await owner.get("/api/v1/review/page", params={"tab": "proposed", "per_page": 3})).json()
    assert (first["held"], first["proposed"], first["total"], first["page"]) == (2, 7, 7, 1)
    assert first["confident"] == 3  # proposals 3, 5, 7 (ids 4, 6, 8) carry a confidence
    assert [i["movie"]["title"] for i in first["items"]] == ["Movie 3", "Movie 4", "Movie 5"]  # oldest first

    last = (
        await owner.get("/api/v1/review/page", params={"tab": "proposed", "per_page": 3, "page": 3})
    ).json()
    assert [i["movie"]["title"] for i in last["items"]] == ["Movie 9"]
    beyond = (
        await owner.get("/api/v1/review/page", params={"tab": "proposed", "per_page": 3, "page": 9})
    ).json()
    assert beyond["page"] == 3 and beyond["items"] == last["items"]  # the last movies were just decided

    held = (await owner.get("/api/v1/review/page")).json()
    assert held["total"] == 2 and [i["status"] for i in held["items"]] == ["held", "held"]
    assert (await owner.get("/api/v1/review/page", params={"per_page": 500})).status_code == 422
