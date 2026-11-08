"""The owner's choices on a decision, shared by the app and the email links."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core.errors import Conflict, NotFound
from triage.domain import audit
from triage.domain import decisions as d
from triage.domain.categories import to_def
from triage.models import Category, Decision
from triage.worker import queue

INTAKE = "intake"


async def choose(db: AsyncSession, decision: Decision, choice: int | str) -> None:
    """``choice`` is a category id, or ``"intake"`` to leave the movie where it is."""
    if decision.status not in {d.HELD, d.PROPOSED, d.FAILED}:
        raise Conflict("This movie was already decided", code="already_decided")
    if choice == INTAKE:
        if decision.status == d.FAILED:
            raise Conflict("Retry the move or pick a category", code="invalid_choice")
        if decision.source == "intake" and decision.status == d.HELD:
            await d.transition(db, decision, d.LEFT_IN_INTAKE)
            action = "leave"
        else:
            await d.transition(db, decision, d.DISMISSED)
            action = "dismiss"
        decision.actor = "owner"
        await audit.record(
            db, actor="owner", action=action, radarr_id=decision.radarr_id, decision_id=decision.id
        )
        return

    category = await db.get(Category, int(choice))
    if category is None or category.deleted_at is not None or not category.root_folder_path:
        raise NotFound("This category does not exist or has no library", code="unknown_category")
    snapshot = list(decision.categories_snapshot or [])
    if not any(c.get("id") == category.id for c in snapshot):
        snapshot.append(to_def(category).to_dict())
        decision.categories_snapshot = snapshot
    decision.target_category_id = category.id
    decision.target_root_folder = category.root_folder_path
    decision.actor = "owner"
    decision.error = None
    await d.transition(db, decision, d.MOVING)
    await queue.enqueue(db, "move", {"decision_id": decision.id})


async def category_by_key(db: AsyncSession, key: str) -> Category | None:
    category: Category | None = await db.scalar(
        select(Category).where(Category.key == key, Category.deleted_at.is_(None))
    )
    return category
