"""The decision state machine (data-model.md). Every status change goes through ``transition``
so forbidden moves (a held movie moved without the owner, a simulation applied…) cannot happen.
"""

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.core.errors import Conflict
from triage.models import Decision, ReviewLink

PROPOSED = "proposed"
HELD = "held"
MOVING = "moving"
MOVED = "moved"
FAILED = "failed"
DISMISSED = "dismissed"
LEFT_IN_INTAKE = "left_in_intake"
SUPERSEDED = "superseded"
SIMULATED = "simulated"
IN_PLACE = "in_place"
CORRECTED = "corrected"

TRANSITIONS: dict[str, set[str]] = {
    PROPOSED: {MOVING, DISMISSED, SUPERSEDED},
    HELD: {MOVING, LEFT_IN_INTAKE, SUPERSEDED},
    MOVING: {MOVED, FAILED, SUPERSEDED},
    FAILED: {MOVING, SUPERSEDED},
    MOVED: {CORRECTED},
    IN_PLACE: set(),
    SIMULATED: set(),
    DISMISSED: set(),
    LEFT_IN_INTAKE: set(),
    SUPERSEDED: set(),
    CORRECTED: set(),
}

OPEN = {PROPOSED, HELD, MOVING, FAILED}
AWAITING_OWNER = {PROPOSED, HELD}


def can_transition(current: str, new: str) -> bool:
    return new in TRANSITIONS.get(current, set())


async def transition(db: AsyncSession, decision: Decision, new: str) -> None:
    if not can_transition(decision.status, new):
        raise Conflict(
            f"A decision {decision.status} cannot become {new}",
            code="invalid_transition",
            details={"from": decision.status, "to": new},
        )
    previous = decision.status
    decision.status = new
    if previous in AWAITING_OWNER:
        await revoke_links(db, decision.id)
    if new in {MOVED, DISMISSED, LEFT_IN_INTAKE, SUPERSEDED, CORRECTED, FAILED}:
        decision.decided_at = clock.now()
    await db.flush()


async def revoke_links(db: AsyncSession, decision_id: int) -> None:
    await db.execute(
        update(ReviewLink)
        .where(
            ReviewLink.decision_id == decision_id,
            ReviewLink.used_at.is_(None),
            ReviewLink.revoked_at.is_(None),
        )
        .values(revoked_at=clock.now())
    )
