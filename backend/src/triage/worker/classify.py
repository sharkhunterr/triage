"""Classify the movie of an arrival and route the decision: move, propose, or hold."""

from sqlalchemy import select

from triage.core import clock
from triage.core.logging import radarr_id_var
from triage.core.settings import same_folder
from triage.domain import arrivals
from triage.domain import decisions as d
from triage.domain.classify import Classification, classify_movie
from triage.models import Arrival, Decision, WorkItem
from triage.worker import queue
from triage.worker.runner import JobContext


def new_decision(radarr_id: int, source: str, result: Classification, from_folder: str | None) -> Decision:
    return Decision(
        radarr_id=radarr_id,
        source=source,
        from_root_folder=from_folder,
        signals=result.signals,
        ai=result.ai,
        scores=result.scores,
        reasons=result.reasons,
        top_category_id=result.top.id if result.top else None,
        confidence=result.confidence,
        categories_snapshot=result.snapshot,
        status=d.HELD,
        actor="triage",
        target_category_id=result.top.id if result.top else None,
        target_root_folder=result.target_folder,
        created_at=clock.now(),
    )


async def classify_job(ctx: JobContext, item: WorkItem) -> None:
    arrival = await ctx.db.get(Arrival, item.ref["arrival_id"])
    if arrival is None or arrival.closed_at is not None:
        return
    radarr_id_var.set(arrival.radarr_id)
    already = await ctx.db.scalar(
        select(Decision.id).where(Decision.arrival_id == arrival.id, Decision.status != d.SUPERSEDED).limit(1)
    )
    if already is not None:
        return  # idempotent: one decision per arrival
    assert ctx.adapters.radarr is not None
    movie = await ctx.adapters.radarr.movie(arrival.radarr_id)
    if movie is None:
        await arrivals.close(ctx.db, arrival, "removed_from_radarr")
        return
    if not same_folder(movie.root_folder_path, arrival.intake_path):
        await arrivals.close(ctx.db, arrival, "moved_elsewhere")
        return
    ref = await arrivals.upsert_movie(ctx.db, movie)

    result = await classify_movie(ctx.db, ctx.settings, ctx.adapters, movie)
    decision = new_decision(movie.id, "intake", result, arrival.intake_path)
    decision.arrival_id = arrival.id
    if ref.corrected:
        # The owner corrected an earlier automatic move: never sort this movie on its own again.
        decision.reasons = [*decision.reasons, {"code": "corrected_before"}]
        decision.status = d.PROPOSED if result.conclusive else d.HELD
    elif result.conclusive and ctx.settings.sorting.mode == "automatic":
        decision.status = d.MOVING
    elif result.conclusive:
        decision.status = d.PROPOSED
    else:
        decision.status = d.HELD
    ctx.db.add(decision)
    await ctx.db.flush()
    if decision.status == d.MOVING:
        await queue.enqueue(ctx.db, "move", {"decision_id": decision.id})
