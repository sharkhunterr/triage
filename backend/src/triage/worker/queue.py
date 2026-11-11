"""Persistent work queue (research R9): one item at a time, exponential backoff, restart-safe."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.models import WorkItem
from triage.models.base import UTCDateTime

MAX_ATTEMPTS = 8
BASE_DELAY_S = 60
MAX_DELAY_S = 3600

PENDING = "pending"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"  # stopped by the owner before it ran


def backoff(attempts: int) -> timedelta:
    """1 min, 2, 4, 8 … capped at 1 h, for the ``attempts``-th failure."""
    return timedelta(seconds=min(BASE_DELAY_S * 2 ** max(attempts - 1, 0), MAX_DELAY_S))


async def enqueue(db: AsyncSession, kind: str, ref: dict[str, Any], *, delay_s: float = 0) -> WorkItem:
    now = clock.now()
    item = WorkItem(
        kind=kind,
        ref=ref,
        state=PENDING,
        attempts=0,
        next_attempt_at=now + timedelta(seconds=delay_s),
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    await db.flush()
    return item


# Analyses can be long (an AI call each): what the owner is waiting for goes first.
BACKGROUND = ("classify", "scan_start", "scan_movie", "refresh_titles", "seerr_requests")
# What the owner may stop from the interface; a move or an email, once queued, always goes through.
STOPPABLE = BACKGROUND
_priority = case((WorkItem.kind.in_(BACKGROUND), 1), else_=0)


async def claim_next(db: AsyncSession) -> WorkItem | None:
    item = (
        await db.scalars(
            select(WorkItem)
            .where(WorkItem.state == PENDING, WorkItem.next_attempt_at <= clock.now())
            .order_by(_priority, WorkItem.next_attempt_at, WorkItem.id)
            .limit(1)
        )
    ).first()
    if item is not None:
        item.state = RUNNING
        item.updated_at = clock.now()
        await db.flush()
    return item


async def complete(db: AsyncSession, item: WorkItem) -> None:
    item.state = DONE
    item.last_error = None
    item.updated_at = clock.now()
    await db.flush()


async def fail(db: AsyncSession, item: WorkItem, error: str, *, retryable: bool = True) -> bool:
    """Record a failure. Returns True when the item will be retried."""
    item.attempts += 1
    item.last_error = error[:2000]
    item.updated_at = clock.now()
    if retryable and item.attempts < MAX_ATTEMPTS:
        item.state = PENDING
        item.next_attempt_at = clock.now() + backoff(item.attempts)
        await db.flush()
        return True
    item.state = FAILED
    await db.flush()
    return False


async def retry_now(db: AsyncSession, item: WorkItem) -> None:
    item.state = PENDING
    item.attempts = 0
    item.next_attempt_at = clock.now()
    item.updated_at = clock.now()
    await db.flush()


async def cancel(db: AsyncSession, kinds: tuple[str, ...], **ref: Any) -> int:
    """Queued items of these kinds (and this ref) that will not run. Returns how many."""
    items = await db.scalars(select(WorkItem).where(WorkItem.kind.in_(kinds), WorkItem.state == PENDING))
    cancelled = 0
    for item in items:
        if all(item.ref.get(k) == v for k, v in ref.items()):
            item.state = CANCELLED
            item.updated_at = clock.now()
            cancelled += 1
    await db.flush()
    return cancelled


async def pending(db: AsyncSession) -> list[WorkItem]:
    return list(await db.scalars(select(WorkItem).where(WorkItem.state == PENDING).order_by(WorkItem.id)))


async def recover(db: AsyncSession) -> int:
    """Items left running by a stopped process go back to pending."""
    result = await db.execute(
        update(WorkItem).where(WorkItem.state == RUNNING).values(state=PENDING, updated_at=clock.now())
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def has_open(db: AsyncSession, kind: str, **ref: Any) -> bool:
    items = await db.scalars(
        select(WorkItem).where(WorkItem.kind == kind, WorkItem.state.in_([PENDING, RUNNING]))
    )
    return any(all(i.ref.get(k) == v for k, v in ref.items()) for i in items)


async def next_due(db: AsyncSession) -> datetime | None:
    due: datetime | None = await db.scalar(
        select(func.min(WorkItem.next_attempt_at, type_=UTCDateTime())).where(WorkItem.state == PENDING)
    )
    return due


async def counts(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(select(WorkItem.state, func.count()).group_by(WorkItem.state))
    return {state: int(n) for state, n in rows.all()}
