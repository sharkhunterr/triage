"""Status page, "check now", retry of failed work (contracts/http-api.md — Status & operations)."""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select

from triage.adapters.types import ServiceError
from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core.activity import Entry
from triage.core.errors import NotFound
from triage.domain import decisions as d
from triage.domain.categories import active
from triage.domain.health import HealthCache, folder_warnings
from triage.models import Decision, WorkItem
from triage.worker import queue, stop

router = APIRouter(tags=["status"], dependencies=[Owner])


class ServiceOut(BaseModel):
    state: str
    detail: str
    checked_at: datetime | None


class FailedItem(BaseModel):
    id: int
    kind: str
    ref: dict[str, Any]
    attempts: int
    last_error: str | None
    updated_at: datetime


class StatusOut(BaseModel):
    mode: str
    services: dict[str, ServiceOut]
    last_poll_at: datetime | None
    next_poll_at: datetime | None
    last_poll_error: str | None
    queue: dict[str, int]
    failed_items: list[FailedItem]
    folder_warnings: list[dict[str, str]]


def _cache(request: Request) -> HealthCache:
    cache: HealthCache | None = getattr(request.app.state, "health_cache", None)
    if cache is None:
        cache = HealthCache()
        request.app.state.health_cache = cache
    return cache


@router.get("/status", response_model=StatusOut)
async def status(
    request: Request, db: Db, state: State, settings: Settings, adapters: AdaptersDep
) -> StatusOut:
    services = await _cache(request).check(adapters)
    warnings: list[dict[str, str]] = []
    if adapters.radarr is not None:
        try:
            warnings = folder_warnings(await active(db), await adapters.radarr.root_folders())
        except ServiceError:
            warnings = []
    failed = await db.scalars(
        select(WorkItem).where(WorkItem.state == queue.FAILED).order_by(WorkItem.updated_at.desc()).limit(50)
    )
    worker = state.worker
    return StatusOut(
        mode=settings.sorting.mode,
        services={name: ServiceOut(**s.__dict__) for name, s in services.items()},
        last_poll_at=worker.last_poll_at,
        next_poll_at=worker.next_poll_at,
        last_poll_error=worker.last_poll_error,
        queue=await queue.counts(db),
        failed_items=[
            FailedItem(
                id=i.id,
                kind=i.kind,
                ref=i.ref,
                attempts=i.attempts,
                last_error=i.last_error,
                updated_at=i.updated_at,
            )
            for i in failed
        ],
        folder_warnings=warnings,
    )


@router.post("/poll", status_code=204)
async def poll_now(request: Request, state: State) -> None:
    _cache(request).clear()
    state.worker.wake()


@router.post("/work-items/{item_id}/retry", status_code=204)
async def retry(item_id: int, db: Db, state: State) -> None:
    item = await db.get(WorkItem, item_id)
    if item is None or item.state != queue.FAILED:
        raise NotFound("No failed work item with this id")
    await queue.retry_now(db, item)
    decision = await db.get(Decision, item.ref.get("decision_id")) if item.kind == "move" else None
    if decision is not None and decision.status == d.FAILED:
        await d.transition(db, decision, d.MOVING)  # the move is being tried again
    await db.commit()
    state.worker.wake()


class StepOut(BaseModel):
    name: str
    state: str
    detail: str | None
    ms: int | None


class EntryOut(BaseModel):
    id: int
    kind: str
    title: str | None
    radarr_id: int | None
    started_at: datetime
    finished_at: datetime | None
    outcome: str | None
    decision_id: int | None
    error: str | None
    retry: bool
    scan_id: int | None
    stoppable: bool  # running, and the owner may stop it
    steps: list[StepOut]


class RunOut(BaseModel):
    started_at: datetime
    finished_at: datetime | None
    done: int
    failed: int
    pending: int


class QueuedOut(BaseModel):
    kind: str  # the group: classify, scan (one check), refresh_titles, seerr_requests, move…
    scan_id: int | None
    folder: str | None  # a check's library
    count: int
    stoppable: bool


class ActivityOut(BaseModel):
    running: EntryOut | None
    run: RunOut | None
    recent: list[EntryOut]
    queue: list[QueuedOut]


def _entry(entry: Entry) -> EntryOut:
    return EntryOut(
        **{k: v for k, v in entry.__dict__.items() if k != "steps"},
        # a job of the worker (an analysis asked from the movie page answers its own request)
        stoppable=entry.id != 0 and entry.finished_at is None and entry.kind in queue.STOPPABLE,
        steps=[StepOut(**s.__dict__) for s in entry.steps],
    )


@router.get("/activity", response_model=ActivityOut)
async def activity(db: Db, state: State) -> ActivityOut:
    """What the worker is doing now, how far the current run is, and the last jobs with their steps."""
    tracker = state.worker.activity
    pending = (await queue.counts(db)).get(queue.PENDING, 0)
    run = tracker.run
    return ActivityOut(
        running=_entry(tracker.running) if tracker.running else None,
        run=RunOut(**run.__dict__, pending=pending) if run else None,
        recent=[_entry(e) for e in tracker.recent],
        queue=[QueuedOut(**g) for g in await stop.queued(db)],
    )


class StopBody(BaseModel):
    kind: Literal["all"] | stop.Group
    scan_id: int | None = None  # one check (kind "scan"); every check without it


class Stopped(BaseModel):
    stopped: int


@router.post("/activity/stop", response_model=Stopped)
async def stop_work(body: StopBody, db: Db, state: State) -> Stopped:
    """Stops a group of work: the queued items are cancelled, the running one is interrupted.
    Moves and emails never stop."""
    groups = list(stop.GROUPS) if body.kind == "all" else [body.kind]
    count = 0
    for group in groups:
        count += await stop.cancel(db, group, body.scan_id if group == "scan" else None)
    await db.commit()
    kinds = tuple(k for g in groups for k in stop.GROUPS[g])
    scan_id = body.scan_id if body.kind == "scan" else None
    count += state.worker.interrupt(kinds, scan_id)
    return Stopped(stopped=count)
