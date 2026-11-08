from datetime import timedelta

from tests.conftest import Env
from triage.models import WorkItem
from triage.worker import queue
from triage.worker.runner import JobContext, JobError


def test_backoff_doubles_from_one_minute_and_caps_at_one_hour():
    assert [queue.backoff(n).total_seconds() for n in (1, 2, 3, 4, 7, 8)] == [60, 120, 240, 480, 3600, 3600]


async def test_failures_are_retried_with_backoff_then_marked_failed(env: Env):
    async with env.state.session_factory() as db:
        item = await queue.enqueue(db, "noop", {})
        for attempt in range(1, queue.MAX_ATTEMPTS):
            assert await queue.fail(db, item, "boom")
            assert item.state == queue.PENDING
            assert item.next_attempt_at == env.clock.current + queue.backoff(attempt)
        assert not await queue.fail(db, item, "boom")
        assert item.state == queue.FAILED


async def test_items_are_claimed_only_when_due(env: Env):
    async with env.state.session_factory() as db:
        await queue.enqueue(db, "later", {}, delay_s=120)
        first = await queue.enqueue(db, "now", {})
        claimed = await queue.claim_next(db)
        assert claimed is not None and claimed.id == first.id
        assert await queue.claim_next(db) is None
        env.clock.advance(minutes=3)
        later = await queue.claim_next(db)
        assert later is not None and later.kind == "later"


async def test_restart_resumes_running_items(env: Env):
    async with env.state.session_factory() as db:
        item = await queue.enqueue(db, "noop", {})
        await queue.claim_next(db)
        assert item.state == queue.RUNNING
        assert await queue.recover(db) == 1
        await db.refresh(item)
        assert item.state == queue.PENDING


async def test_worker_records_job_errors_and_retries(env: Env):
    calls: list[int] = []

    async def flaky(_ctx: JobContext, item: WorkItem) -> None:
        calls.append(item.id)
        if len(calls) == 1:
            raise JobError("first try fails", retryable=True)

    env.state.worker.handlers["flaky"] = flaky
    async with env.state.session_factory() as db:
        item = await queue.enqueue(db, "flaky", {})
        await db.commit()
    await env.state.worker.drain()
    async with env.state.session_factory() as db:
        stored = await db.get(WorkItem, item.id)
        assert stored is not None
        assert (stored.state, stored.attempts, stored.last_error) == ("pending", 1, "first try fails")
    env.clock.advance(seconds=61)
    await env.state.worker.drain()
    async with env.state.session_factory() as db:
        stored = await db.get(WorkItem, item.id)
        assert stored is not None and stored.state == "done"
    assert len(calls) == 2


async def test_unknown_kinds_fail_without_retry(env: Env):
    async with env.state.session_factory() as db:
        item = await queue.enqueue(db, "mystery", {})
        await db.commit()
    await env.state.worker.drain()
    async with env.state.session_factory() as db:
        stored = await db.get(WorkItem, item.id)
        assert stored is not None and stored.state == "failed"
    assert queue.backoff(0) == timedelta(seconds=60)
