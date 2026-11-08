import pytest

from tests.conftest import Env
from triage.core.errors import Conflict
from triage.domain import decisions as d
from triage.models import Decision, MovieRef, ReviewLink

ALLOWED = [
    (d.PROPOSED, d.MOVING),
    (d.PROPOSED, d.DISMISSED),
    (d.HELD, d.MOVING),
    (d.HELD, d.LEFT_IN_INTAKE),
    (d.MOVING, d.MOVED),
    (d.MOVING, d.FAILED),
    (d.FAILED, d.MOVING),
    (d.MOVED, d.CORRECTED),
    (d.HELD, d.SUPERSEDED),
]
FORBIDDEN = [
    (d.SIMULATED, d.MOVING),
    (d.IN_PLACE, d.MOVING),
    (d.DISMISSED, d.MOVING),
    (d.LEFT_IN_INTAKE, d.MOVING),
    (d.MOVED, d.MOVING),
    (d.HELD, d.MOVED),
    (d.PROPOSED, d.MOVED),
    (d.SUPERSEDED, d.MOVING),
]


@pytest.mark.parametrize(("current", "new"), ALLOWED)
def test_allowed(current: str, new: str):
    assert d.can_transition(current, new)


@pytest.mark.parametrize(("current", "new"), FORBIDDEN)
def test_forbidden(current: str, new: str):
    assert not d.can_transition(current, new)


async def _decision(env: Env, status: str) -> tuple[Decision, ReviewLink]:
    async with env.state.session_factory() as db:
        db.add(MovieRef(radarr_id=1, tmdb_id=10, title="T", year=2000, updated_at=env.clock.current))
        await db.flush()
        decision = Decision(
            radarr_id=1,
            source="intake",
            signals=[],
            scores={},
            reasons=[],
            categories_snapshot=[],
            status=status,
            created_at=env.clock.current,
        )
        db.add(decision)
        await db.flush()
        link = ReviewLink(
            token_hash="h", decision_id=decision.id, choice="films", expires_at=env.clock.current
        )
        db.add(link)
        await db.commit()
        return decision, link


async def test_leaving_held_revokes_the_review_links(env: Env):
    decision, link = await _decision(env, d.HELD)
    async with env.state.session_factory() as db:
        stored = await db.get(Decision, decision.id)
        assert stored is not None
        await d.transition(db, stored, d.MOVING)
        await db.commit()
        refreshed = await db.get(ReviewLink, link.token_hash)
        assert refreshed is not None and refreshed.revoked_at is not None


async def test_a_forbidden_transition_raises_conflict(env: Env):
    decision, _ = await _decision(env, d.SIMULATED)
    async with env.state.session_factory() as db:
        stored = await db.get(Decision, decision.id)
        assert stored is not None
        with pytest.raises(Conflict):
            await d.transition(db, stored, d.MOVING)
