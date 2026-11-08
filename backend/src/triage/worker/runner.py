"""The in-process worker: polls Radarr on schedule (or when woken by a webhook), then works
through the queue one item at a time, each in its own transaction (research R9)."""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage.adapters.factory import AdapterFactory
from triage.adapters.types import Adapters, ServiceError
from triage.core import clock
from triage.core.activity import Activity, current_entry
from triage.core.logging import work_item_id_var
from triage.core.settings import AppSettings, load_settings
from triage.models import WorkItem
from triage.worker import queue

log = logging.getLogger(__name__)


@dataclass
class JobContext:
    db: AsyncSession
    settings: AppSettings
    adapters: Adapters


class JobError(Exception):
    """A job failed for a reason that is not a service outage."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


Handler = Callable[[JobContext, WorkItem], Awaitable[None]]
Hook = Callable[[JobContext], Awaitable[None]]


class Worker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapter_factory: AdapterFactory,
        handlers: dict[str, Handler],
        poll: Hook | None = None,
        after_drain: Hook | None = None,
        give_up: dict[str, Handler] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.adapter_factory = adapter_factory
        self.handlers = handlers
        self.give_up = give_up or {}
        self._poll = poll
        self._after_drain = after_drain
        self.activity = Activity()
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self.last_poll_at: datetime | None = None
        self.last_poll_error: str | None = None
        self.next_poll_at: datetime | None = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="triage-worker")

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task is not None:
            await self._task

    def wake(self) -> None:
        """Poll as soon as possible (webhook, "check now")."""
        self.next_poll_at = clock.now()
        self._wake.set()

    # ------------------------------------------------------------------ one round
    async def tick(self, *, poll: bool = False) -> int:
        """Poll when due (or forced), then process every due item. Used by the loop and tests."""
        async with self.session_factory() as db:
            settings = await load_settings(db)
        due = self.next_poll_at is None or self.next_poll_at <= clock.now()
        if self._poll is not None and (poll or due):
            await self.poll(settings)
        processed = await self.drain()
        if self._after_drain is not None:
            async with self.session_factory() as db:
                settings = await load_settings(db)
                await self._after_drain(JobContext(db, settings, self.adapter_factory(settings)))
                await db.commit()
            processed += await self.drain()
        return processed

    async def poll(self, settings: AppSettings) -> None:
        assert self._poll is not None
        self.next_poll_at = clock.now() + timedelta(seconds=settings.sorting.poll_interval_s)
        async with self.session_factory() as db:
            try:
                await self._poll(JobContext(db, settings, self.adapter_factory(settings)))
                await db.commit()
                self.last_poll_error = None
            except ServiceError as exc:
                await db.rollback()
                self.last_poll_error = exc.message
                log.warning("poll failed", extra={"service": exc.service, "error": exc.message})
            self.last_poll_at = clock.now()

    async def drain(self) -> int:
        processed = 0
        while not self._stop.is_set():
            async with self.session_factory() as db:
                item = await queue.claim_next(db)
                await db.commit()
            if item is None:
                self.activity.idle()
                return processed
            await self._process(item.id)
            processed += 1
        return processed

    async def _process(self, item_id: int) -> None:
        token = work_item_id_var.set(item_id)
        try:
            async with self.session_factory() as db:
                item = await db.get(WorkItem, item_id)
                assert item is not None
                settings = await load_settings(db)
                handler = self.handlers.get(item.kind)
                entry = self.activity.start(item_id, item.kind)
                entry_token = current_entry.set(entry)
                try:
                    if handler is None:
                        raise JobError(f"no handler for {item.kind}")
                    await handler(JobContext(db, settings, self.adapter_factory(settings)), item)
                    await queue.complete(db, item)
                    await db.commit()
                    self.activity.finish(entry)
                except (ServiceError, JobError) as exc:
                    await db.rollback()
                    item = await db.get(WorkItem, item_id)
                    assert item is not None
                    message = str(exc)
                    retried = await queue.fail(db, item, message, retryable=exc.retryable)
                    await self._maybe_give_up(db, item, settings, retried)
                    await db.commit()
                    self.activity.finish(entry, error=message, retry=retried)
                    log.warning(
                        "work item failed", extra={"kind": item.kind, "error": message, "retry": retried}
                    )
                except Exception as exc:
                    await db.rollback()
                    item = await db.get(WorkItem, item_id)
                    assert item is not None
                    retried = await queue.fail(db, item, f"{exc.__class__.__name__}: {exc}", retryable=True)
                    await self._maybe_give_up(db, item, settings, retried)
                    await db.commit()
                    self.activity.finish(entry, error=str(exc), retry=retried)
                    log.exception("work item crashed", extra={"kind": item.kind})
                finally:
                    current_entry.reset(entry_token)
        finally:
            work_item_id_var.reset(token)

    async def _maybe_give_up(
        self, db: AsyncSession, item: WorkItem, settings: AppSettings, retried: bool
    ) -> None:
        """An item that will not be retried lets its job record the failure (e.g. decision failed)."""
        handler = self.give_up.get(item.kind)
        if not retried and handler is not None:
            await handler(JobContext(db, settings, self.adapter_factory(settings)), item)

    # ------------------------------------------------------------------ loop
    async def _run(self) -> None:
        async with self.session_factory() as db:
            recovered = await queue.recover(db)
            await db.commit()
        if recovered:
            log.info("resumed interrupted work", extra={"items": recovered})
        while not self._stop.is_set():
            try:
                await self.tick()
            except Exception:
                log.exception("worker round failed")
            await self._sleep()

    async def _sleep(self) -> None:
        async with self.session_factory() as db:
            next_item = await queue.next_due(db)
        candidates = [t for t in (self.next_poll_at, next_item) if t is not None]
        wake_at = min(candidates) if candidates else None
        timeout = 60.0 if wake_at is None else max(0.5, (wake_at - clock.now()).total_seconds())
        self._wake.clear()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._wake.wait(), timeout=min(timeout, 60.0))
