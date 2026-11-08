"""Scans (contracts/http-api.md — Scans)."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from triage.api.decisions import DecisionSummary, summaries
from triage.api.deps import AdaptersDep, Db, Owner, State
from triage.core import clock
from triage.core.errors import Conflict, NotFound, TriageError
from triage.core.settings import normalize_folder, same_folder
from triage.models import Decision, Scan
from triage.worker import queue
from triage.worker.scan import CANCELLED, RUNNING

router = APIRouter(tags=["scans"], dependencies=[Owner])


class ScanIn(BaseModel):
    root_folder_path: str


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    root_folder_path: str
    state: str
    total: int
    done: int
    started_at: datetime
    finished_at: datetime | None


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
    scan = Scan(
        root_folder_path=normalize_folder(body.root_folder_path), state=RUNNING, started_at=clock.now()
    )
    db.add(scan)
    await db.flush()
    await queue.enqueue(db, "scan_start", {"scan_id": scan.id})
    await db.commit()
    state.worker.wake()
    return scan


@router.get("/scans", response_model=list[ScanOut])
async def list_scans(db: Db) -> list[Scan]:
    return list(await db.scalars(select(Scan).order_by(Scan.id.desc()).limit(20)))


async def _scan(db: Db, scan_id: int) -> Scan:
    scan = await db.get(Scan, scan_id)
    if scan is None:
        raise NotFound("Unknown scan")
    return scan


@router.get("/scans/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: int, db: Db) -> Scan:
    return await _scan(db, scan_id)


@router.get("/scans/{scan_id}/results", response_model=list[DecisionSummary])
async def scan_results(scan_id: int, db: Db) -> list[DecisionSummary]:
    await _scan(db, scan_id)
    rows = await db.scalars(select(Decision).where(Decision.scan_id == scan_id).order_by(Decision.id))
    return await summaries(db, list(rows))


@router.post("/scans/{scan_id}/cancel", response_model=ScanOut)
async def cancel_scan(scan_id: int, db: Db) -> Scan:
    scan = await _scan(db, scan_id)
    if scan.state == RUNNING:
        scan.state = CANCELLED
        scan.finished_at = clock.now()
        await db.commit()
    return scan
