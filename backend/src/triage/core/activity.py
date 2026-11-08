"""Live progress of the worker: the job running now, its steps, the last ones done.

Kept in memory only (Constitution XI): it is a window on the work in progress, the decisions and
the audit trail stay the durable record. Jobs report through ``step``/``note``, which do nothing
outside a tracked job, so domain code can call them freely.
"""

import time
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from triage.core import clock

RUNNING, DONE, SKIPPED, FAILED = "running", "done", "skipped", "failed"


@dataclass
class Step:
    name: str
    state: str = RUNNING
    detail: str | None = None
    ms: int | None = None


@dataclass
class Entry:
    id: int
    kind: str
    started_at: datetime
    title: str | None = None
    radarr_id: int | None = None
    steps: list[Step] = field(default_factory=list)
    finished_at: datetime | None = None
    outcome: str | None = None
    decision_id: int | None = None
    error: str | None = None
    retry: bool = False


@dataclass
class Run:
    """A stretch of work, from the queue filling up to the queue being empty again."""

    started_at: datetime
    done: int = 0
    failed: int = 0
    finished_at: datetime | None = None


class Activity:
    def __init__(self, keep: int = 60) -> None:
        self.recent: deque[Entry] = deque(maxlen=keep)
        self.current: Entry | None = None
        self.run: Run | None = None

    def start(self, item_id: int, kind: str) -> Entry:
        if self.run is None or self.run.finished_at is not None:
            self.run = Run(started_at=clock.now())
        self.current = Entry(id=item_id, kind=kind, started_at=clock.now())
        return self.current

    def finish(self, entry: Entry, *, error: str | None = None, retry: bool = False) -> None:
        entry.finished_at = clock.now()
        entry.error, entry.retry = error, retry
        for step in entry.steps:
            if step.state == RUNNING:
                step.state = FAILED if error else DONE
        self.recent.appendleft(entry)
        if self.run is not None:
            self.run.done += 1
            self.run.failed += 1 if error else 0
        if self.current is entry:
            self.current = None

    def idle(self) -> None:
        """The queue is empty: the current run is over."""
        if self.run is not None and self.run.finished_at is None:
            self.run.finished_at = clock.now()


current_entry: ContextVar[Entry | None] = ContextVar("current_entry", default=None)


@contextmanager
def step(name: str, detail: str | None = None) -> Iterator[Step]:
    """Times one step of the current job; set ``.detail`` on the yielded step to describe it."""
    entry = current_entry.get()
    record = Step(name, detail=detail)
    if entry is not None:
        entry.steps.append(record)
    began = time.monotonic()
    try:
        yield record
    except BaseException:
        record.state = FAILED
        raise
    finally:
        record.ms = round((time.monotonic() - began) * 1000)
        if record.state == RUNNING:
            record.state = DONE


def skip(name: str, reason: str) -> None:
    entry = current_entry.get()
    if entry is not None:
        entry.steps.append(Step(name, state=SKIPPED, detail=reason))


def note(**fields: Any) -> None:
    """Fills in the current job: title, radarr_id, outcome, decision_id."""
    entry = current_entry.get()
    if entry is not None:
        for key, value in fields.items():
            setattr(entry, key, value)
