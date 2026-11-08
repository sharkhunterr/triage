"""After a move, check the request portal still tracks the movie (FR-022g). Read-only: the
portal refuses edits of approved requests and would re-send an edited one to Radarr."""

from triage.core import clock
from triage.models import Decision, MovieRef, WorkItem
from triage.worker.runner import JobContext


async def verify_request_job(ctx: JobContext, item: WorkItem) -> None:
    decision = await ctx.db.get(Decision, item.ref["decision_id"])
    if decision is None or ctx.adapters.seerr is None:
        return
    ref = await ctx.db.get(MovieRef, decision.radarr_id)
    if ref is None or not ref.tmdb_id:
        return
    request = await ctx.adapters.seerr.request_for(ref.tmdb_id)
    decision.request_check = {
        "tracked": request is not None,
        "request_id": request.id if request else None,
        "requester": request.requested_by if request else None,
        "status": request.status if request else None,
        "checked_at": clock.now().isoformat(),
    }
