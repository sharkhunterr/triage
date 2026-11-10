"""Owner-started scans of a root folder: proposals only, never a move (FR-022c to FR-022e)."""

from sqlalchemy import select

from triage.core import clock
from triage.core.activity import note, step
from triage.core.logging import radarr_id_var
from triage.core.settings import normalize_folder, same_folder
from triage.domain import decisions as d
from triage.domain.arrivals import upsert_movie
from triage.domain.classify import classify_movie
from triage.models import Decision, Scan, WorkItem
from triage.worker import queue
from triage.worker.classify import new_decision, record_decision
from triage.worker.runner import JobContext

RUNNING = "running"
DONE = "done"
CANCELLED = "cancelled"


async def scan_start_job(ctx: JobContext, item: WorkItem) -> None:
    scan = await ctx.db.get(Scan, item.ref["scan_id"])
    if scan is None or scan.state != RUNNING:
        return
    assert ctx.adapters.radarr is not None
    movies = [
        m
        for m in await ctx.adapters.radarr.movies()
        if same_folder(m.root_folder_path, scan.root_folder_path)
    ]
    scan.total = len(movies)
    if not movies:
        scan.state = DONE
        scan.finished_at = clock.now()
        return
    for movie in sorted(movies, key=lambda m: m.title.casefold()):
        await queue.enqueue(ctx.db, "scan_movie", {"scan_id": scan.id, "radarr_id": movie.id})


async def scan_movie_job(ctx: JobContext, item: WorkItem) -> None:
    scan = await ctx.db.get(Scan, item.ref["scan_id"])
    if scan is None or scan.state != RUNNING:
        return
    radarr_id = item.ref["radarr_id"]
    radarr_id_var.set(radarr_id)
    assert ctx.adapters.radarr is not None
    note(radarr_id=radarr_id)
    with step("radarr") as reading:
        movie = await ctx.adapters.radarr.movie(radarr_id)
        reading.detail = movie.title if movie else None
    if movie is not None:
        note(title=movie.title)
    pending = await ctx.db.scalar(
        select(Decision.id).where(Decision.radarr_id == radarr_id, Decision.status.in_(list(d.OPEN))).limit(1)
    )
    if movie is not None and pending is None and same_folder(movie.root_folder_path, scan.root_folder_path):
        await upsert_movie(ctx.db, movie)
        result = await classify_movie(ctx.db, ctx.settings, ctx.adapters, movie)
        decision = new_decision(movie.id, "scan", result, normalize_folder(scan.root_folder_path))
        decision.scan_id = scan.id
        # its best choice is where it already is: in place, sure or not — a check looks for gaps
        if same_folder(result.target_folder, scan.root_folder_path):
            decision.status = d.IN_PLACE
        elif result.conclusive:
            decision.status = d.PROPOSED
        else:
            decision.status = d.HELD
        ctx.db.add(decision)
        await ctx.db.flush()
        record_decision(decision, result)
    scan.done += 1
    if scan.done >= scan.total:
        scan.state = DONE
        scan.finished_at = clock.now()
