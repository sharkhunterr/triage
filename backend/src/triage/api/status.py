"""Status page, "check now", retry of failed work (contracts/http-api.md — Status & operations)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select

from triage.adapters.types import ServiceError
from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core.errors import NotFound
from triage.domain import decisions as d
from triage.domain.categories import active
from triage.domain.health import HealthCache, folder_warnings
from triage.models import Decision, WorkItem
from triage.worker import queue

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
