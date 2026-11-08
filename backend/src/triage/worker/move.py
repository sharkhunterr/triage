"""Move a movie through Radarr's editor and confirm it before calling it done (research R2)."""

from triage.core.logging import decision_id_var, radarr_id_var
from triage.core.settings import normalize_folder, same_folder
from triage.domain import arrivals, audit
from triage.domain import decisions as d
from triage.models import Arrival, Decision, MovieRef, WorkItem
from triage.worker import queue
from triage.worker.runner import JobContext, JobError


async def move_job(ctx: JobContext, item: WorkItem) -> None:
    decision = await ctx.db.get(Decision, item.ref["decision_id"])
    if decision is None or decision.status != d.MOVING or not decision.target_root_folder:
        return
    decision_id_var.set(decision.id)
    radarr_id_var.set(decision.radarr_id)
    assert ctx.adapters.radarr is not None
    radarr = ctx.adapters.radarr
    target = normalize_folder(decision.target_root_folder)
    arrival = await ctx.db.get(Arrival, decision.arrival_id) if decision.arrival_id else None

    movie = await radarr.movie(decision.radarr_id)
    if movie is None:
        await d.transition(ctx.db, decision, d.SUPERSEDED)
        if arrival is not None:
            await arrivals.close(ctx.db, arrival, "removed_from_radarr")
        return
    origin = movie.root_folder_path
    if not same_folder(origin, target):
        # Only move a movie that is still where the decision found it.
        if decision.from_root_folder and not same_folder(origin, decision.from_root_folder):
            await d.transition(ctx.db, decision, d.SUPERSEDED)
            if arrival is not None:
                await arrivals.close(ctx.db, arrival, "moved_elsewhere")
            return
        await radarr.move(movie.id, target)
        after = await radarr.movie(movie.id)
        if after is None or not same_folder(after.root_folder_path, target):
            raise JobError("Radarr did not move the movie to the target folder", retryable=True)

    await d.transition(ctx.db, decision, d.MOVED)
    decision.error = None
    ref = await ctx.db.get(MovieRef, movie.id)
    if ref is not None:
        ref.root_folder_path = target
    if arrival is not None and not same_folder(target, arrival.intake_path):
        await arrivals.close(ctx.db, arrival, "moved_by_triage")
    await audit.record(
        ctx.db,
        actor=decision.actor,
        action="move",
        radarr_id=movie.id,
        decision_id=decision.id,
        from_path=normalize_folder(origin) if origin else None,
        to_path=target,
    )
    if ctx.adapters.seerr is not None:
        await queue.enqueue(ctx.db, "verify_request", {"decision_id": decision.id})


async def move_given_up(ctx: JobContext, item: WorkItem) -> None:
    """The move failed after every retry: the decision shows it and can be retried."""
    decision = await ctx.db.get(Decision, item.ref["decision_id"])
    if decision is None or decision.status != d.MOVING:
        return
    decision.error = item.last_error
    await d.transition(ctx.db, decision, d.FAILED)
    await audit.record(
        ctx.db,
        actor=decision.actor,
        action="move",
        radarr_id=decision.radarr_id,
        decision_id=decision.id,
        to_path=decision.target_root_folder,
        result="failed",
        detail=item.last_error,
    )
