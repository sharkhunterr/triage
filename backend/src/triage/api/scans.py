"""Scans (contracts/http-api.md — Scans)."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from triage.api.decisions import DecisionSummary, summaries
from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core import clock
from triage.core.errors import Conflict, NotFound, TriageError
from triage.core.settings import normalize_folder, same_folder
from triage.domain import decisions as d
from triage.models import Decision, Scan
from triage.worker import queue, stop
from triage.worker.scan import RUNNING

router = APIRouter(tags=["scans"], dependencies=[Owner])


class ScanIn(BaseModel):
    root_folder_path: str
    respect_locks: bool = True  # movies the owner locked in this library stay in place


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    root_folder_path: str
    state: str
    total: int
    done: int
    started_at: datetime
    finished_at: datetime | None
    respect_locks: bool = True
    waiting: int = 0  # gaps and doubts still to settle


async def _out(db: Db, scans: list[Scan]) -> list[ScanOut]:
    waiting = dict(
        (
            await db.execute(
                select(Decision.scan_id, func.count())
                .where(Decision.scan_id.in_([s.id for s in scans]), Decision.status.in_([d.HELD, d.PROPOSED]))
                .group_by(Decision.scan_id)
            )
        )
        .tuples()
        .all()
    )
    return [
        ScanOut.model_validate(s).model_copy(update={"waiting": int(waiting.get(s.id, 0))}) for s in scans
    ]


class InvalidFolder(TriageError):
    status_code = 422
    code = "unknown_root_folder"


@router.post("/scans", response_model=ScanOut, status_code=202)
async def start_scan(body: ScanIn, db: Db, adapters: AdaptersDep, state: State) -> Scan:
    running = await db.scalar(select(Scan.id).where(Scan.state == RUNNING).limit(1))
    if running is not None:
        raise Conflict("A scan is already running", code="scan_running", details={"scan_id": running})
    if adapters.radarr is None:
        raise NotFound("Connect Radarr first", code="radarr_not_configured")
    folders = [f.path for f in await adapters.radarr.root_folders()]
    if not any(same_folder(body.root_folder_path, f) for f in folders):
        raise InvalidFolder("This folder is not one of Radarr's root folders")
    folder = normalize_folder(body.root_folder_path)
    # a new check of a folder replaces what the last one left undecided there
    earlier = select(Scan.id).where(Scan.root_folder_path == folder)
    for stale in await db.scalars(
        select(Decision).where(Decision.scan_id.in_(earlier), Decision.status.in_([d.HELD, d.PROPOSED]))
    ):
        await d.transition(db, stale, d.SUPERSEDED)
    scan = Scan(
        root_folder_path=folder, state=RUNNING, respect_locks=body.respect_locks, started_at=clock.now()
    )
    db.add(scan)
    await db.flush()
    await queue.enqueue(db, "scan_start", {"scan_id": scan.id})
    await db.commit()
    state.worker.wake()
    return scan


@router.get("/scans", response_model=list[ScanOut])
async def list_scans(db: Db) -> list[ScanOut]:
    return await _out(db, list(await db.scalars(select(Scan).order_by(Scan.id.desc()).limit(20))))


async def _scan(db: Db, scan_id: int) -> Scan:
    scan = await db.get(Scan, scan_id)
    if scan is None:
        raise NotFound("Unknown scan")
    return scan


@router.get("/scans/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: int, db: Db) -> ScanOut:
    (out,) = await _out(db, [await _scan(db, scan_id)])
    return out


@router.get("/scans/{scan_id}/results", response_model=list[DecisionSummary])
async def scan_results(scan_id: int, db: Db) -> list[DecisionSummary]:
    await _scan(db, scan_id)
    rows = await db.scalars(select(Decision).where(Decision.scan_id == scan_id).order_by(Decision.id))
    return await summaries(db, list(rows))


class ScanPage(BaseModel):
    """One page of a check's tab, and how many movies each tab holds."""

    items: list[DecisionSummary]
    total: int  # in the tab asked
    page: int
    per_page: int
    gaps: int  # sure they belong in another library
    held: int  # in doubt
    in_place: int
    applied: int  # gaps already sent to their library
    confident: int  # gaps sure enough to apply in one go


TABS = {"gaps": [d.PROPOSED], "held": [d.HELD], "in_place": [d.IN_PLACE]}


@router.get("/scans/{scan_id}/page", response_model=ScanPage)
async def scan_page(
    scan_id: int,
    db: Db,
    settings: Settings,
    tab: Literal["gaps", "held", "in_place"] = "gaps",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 24,
) -> ScanPage:
    """A check's results a page at a time, like the review queue: the gaps first."""
    await _scan(db, scan_id)
    counts = dict(
        (
            await db.execute(
                select(Decision.status, func.count())
                .where(Decision.scan_id == scan_id)
                .group_by(Decision.status)
            )
        )
        .tuples()
        .all()
    )
    confident = await db.scalar(
        select(func.count()).where(
            Decision.scan_id == scan_id,
            Decision.status == d.PROPOSED,
            Decision.confidence >= settings.sorting.threshold,
        )
    )
    statuses = TABS[tab]
    total = sum(int(counts.get(s, 0)) for s in statuses)
    page = min(page, max(1, -(-total // per_page)))
    rows = await db.scalars(
        select(Decision)
        .where(Decision.scan_id == scan_id, Decision.status.in_(statuses))
        .order_by(Decision.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return ScanPage(
        items=await summaries(db, list(rows)),
        total=total,
        page=page,
        per_page=per_page,
        gaps=int(counts.get(d.PROPOSED, 0)),
        held=int(counts.get(d.HELD, 0)),
        in_place=int(counts.get(d.IN_PLACE, 0)),
        applied=sum(int(counts.get(s, 0)) for s in (d.MOVING, d.MOVED, d.FAILED)),
        confident=int(confident or 0),
    )


@router.post("/scans/{scan_id}/cancel", response_model=ScanOut)
async def cancel_scan(scan_id: int, db: Db, state: State) -> Scan:
    scan = await _scan(db, scan_id)
    if scan.state == RUNNING:
        await stop.cancel(db, "scan", scan_id)
        await db.commit()
        state.worker.interrupt(stop.GROUPS["scan"], scan_id)
        await db.refresh(scan)
    return scan
