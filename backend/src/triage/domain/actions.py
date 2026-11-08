"""The owner's choices on a decision, shared by the app and the email links."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.core.errors import Conflict, NotFound
from triage.core.settings import same_folder
from triage.domain import audit
from triage.domain import decisions as d
from triage.domain.categories import to_def
from triage.models import Category, Decision, MovieRef
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


async def correct(
    db: AsyncSession, decision: Decision, choice: int | str, intake_folders: list[str]
) -> Decision:
    """Move a movie Triage moved somewhere else (FR-021). The movie is marked corrected: Triage
    will only ever propose for it from now on. Returns the correction decision."""
    if decision.status != d.MOVED:
        raise Conflict("Only a moved movie can be corrected", code="not_moved")
    snapshot = list(decision.categories_snapshot or [])
    if choice == INTAKE:
        target = decision.from_root_folder if decision.source == "intake" else None
        target = target or (intake_folders[0] if intake_folders else None)
        if not target:
            raise Conflict("No intake folder is configured", code="no_intake")
        category_id = None
    else:
        category = await db.get(Category, int(choice))
        if category is None or category.deleted_at is not None or not category.root_folder_path:
            raise NotFound("This category does not exist or has no library", code="unknown_category")
        target = category.root_folder_path
        category_id = category.id
        if not any(c.get("id") == category.id for c in snapshot):
            snapshot.append(to_def(category).to_dict())

    return await _move_again(db, decision, target, category_id, snapshot)


async def revert(db: AsyncSession, decision: Decision) -> Decision:
    """Undo a move: the movie goes back to the very folder it was moved from (the intake folder,
    or the library a scan found it in). Like any correction, Triage only proposes for it afterwards."""
    if decision.status != d.MOVED:
        raise Conflict("Only a moved movie can be undone", code="not_moved")
    if not decision.from_root_folder:
        raise Conflict("The folder this movie came from is unknown", code="no_origin")
    snapshot = list(decision.categories_snapshot or [])
    origin = next(
        (
            c
            for c in await db.scalars(select(Category).where(Category.deleted_at.is_(None)))
            if same_folder(c.root_folder_path, decision.from_root_folder)
        ),
        None,
    )
    if origin is not None and not any(c.get("id") == origin.id for c in snapshot):
        snapshot.append(to_def(origin).to_dict())
    category_id = origin.id if origin is not None else None
    return await _move_again(db, decision, decision.from_root_folder, category_id, snapshot)


async def revertable(db: AsyncSession, since: datetime | None = None) -> list[Decision]:
    """Moves that can be undone, newest first. The owner's own corrections are left out."""
    query = select(Decision).where(
        Decision.status == d.MOVED,
        Decision.source != "correction",
        Decision.from_root_folder.is_not(None),
    )
    if since is not None:
        query = query.where(Decision.decided_at >= since)
    return list(await db.scalars(query.order_by(Decision.decided_at.desc(), Decision.id.desc())))


async def _move_again(
    db: AsyncSession, decision: Decision, target: str, category_id: int | None, snapshot: list[Any]
) -> Decision:
    ref = await db.get(MovieRef, decision.radarr_id)
    if ref is not None:
        ref.corrected = True
    correction = Decision(
        radarr_id=decision.radarr_id,
        source="correction",
        from_root_folder=decision.target_root_folder,
        signals=decision.signals,
        ai=decision.ai,
        scores=decision.scores,
        reasons=[],
        top_category_id=decision.top_category_id,
        confidence=decision.confidence,
        categories_snapshot=snapshot,
        status=d.MOVING,
        actor="owner",
        target_category_id=category_id,
        target_root_folder=target,
        created_at=clock.now(),
    )
    db.add(correction)
    await d.transition(db, decision, d.CORRECTED)
    await db.flush()
    await queue.enqueue(db, "move", {"decision_id": correction.id})
    return correction
