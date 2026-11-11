"""Stopping work from the Activity page. The work is shown and stopped by group: the analyses, a
check (its start and its movies), the title refreshes, the Seerr requests. The queued items are
cancelled; the one running is interrupted by the worker (``Worker.interrupt``). A stopped movie
stays where it is: a new movie can be analysed again, a check started again."""

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.models import Scan
from triage.worker import queue
from triage.worker.scan import CANCELLED, RUNNING

Group = Literal["classify", "scan", "refresh_titles", "seerr_requests"]
GROUPS: dict[str, tuple[str, ...]] = {
    "classify": ("classify",),
    "scan": ("scan_start", "scan_movie"),
    "refresh_titles": ("refresh_titles",),
    "seerr_requests": ("seerr_requests",),
}
assert {k for kinds in GROUPS.values() for k in kinds} == set(queue.STOPPABLE)


def group_of(kind: str) -> str:
    return next((group for group, kinds in GROUPS.items() if kind in kinds), kind)


async def queued(db: AsyncSession) -> list[dict[str, Any]]:
    """What waits, by group (a check apart from another), in the order it was queued."""
    groups: dict[tuple[str, int | None], dict[str, Any]] = {}
    for item in await queue.pending(db):
        group = group_of(item.kind)
        scan_id = item.ref.get("scan_id") if group == "scan" else None
        entry = groups.setdefault(
            (group, scan_id),
            {"kind": group, "scan_id": scan_id, "folder": None, "count": 0, "stoppable": group in GROUPS},
        )
        entry["count"] += 1
    scans = [g for g in groups.values() if g["scan_id"] is not None]
    if scans:
        rows = await db.execute(
            select(Scan.id, Scan.root_folder_path).where(Scan.id.in_([g["scan_id"] for g in scans]))
        )
        folders = dict(rows.tuples().all())
        for g in scans:
            g["folder"] = folders.get(g["scan_id"])
    return list(groups.values())


async def cancel(db: AsyncSession, group: str, scan_id: int | None = None) -> int:
    """Cancels the queued items of a group (of one check); a check stopped is over."""
    if group != "scan":
        return await queue.cancel(db, GROUPS[group])
    ref = {} if scan_id is None else {"scan_id": scan_id}
    cancelled = await queue.cancel(db, GROUPS["scan"], **ref)
    scans = select(Scan).where(Scan.state == RUNNING)
    for scan in await db.scalars(scans if scan_id is None else scans.where(Scan.id == scan_id)):
        scan.state, scan.finished_at = CANCELLED, clock.now()
    await db.flush()
    return cancelled
