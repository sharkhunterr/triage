"""Who asked for each movie in Seerr (Overseerr / Jellyseerr), and when: every movie not looked up yet
gets its request — all the requests read in one pass, read-only. A movie no one requested is marked
looked up all the same, so it is not asked again."""

from sqlalchemy import exists, select

from triage.core import clock
from triage.core.activity import step
from triage.models import MovieRef, WorkItem
from triage.worker import queue
from triage.worker.runner import JobContext

KIND = "seerr_requests"
UNCHECKED = (MovieRef.tmdb_id.is_not(None), MovieRef.request_checked_at.is_(None))


async def seerr_requests_job(ctx: JobContext, item: WorkItem) -> None:
    if ctx.adapters.seerr is None:
        return
    wanted = list(await ctx.db.scalars(select(MovieRef).where(*UNCHECKED)))
    if not wanted:
        return
    with step("requests") as requests:
        latest = await ctx.adapters.seerr.movie_requests()
        now = clock.now()
        found = 0
        for ref in wanted:
            request = latest.get(ref.tmdb_id or 0)
            if request is not None:
                ref.requested_by = request.requested_by
                ref.requested_at = request.requested_at
                found += 1
            ref.request_checked_at = now
        requests.detail = f"{found} / {len(wanted)}"


async def look_up_requests(ctx: JobContext) -> None:
    """After a poll: the movies not looked up yet in Seerr get their request, in the background."""
    if ctx.adapters.seerr is None or await queue.has_open(ctx.db, KIND):
        return
    if await ctx.db.scalar(select(exists().where(*UNCHECKED))):
        await queue.enqueue(ctx.db, KIND, {})
