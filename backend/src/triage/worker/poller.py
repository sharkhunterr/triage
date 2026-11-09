"""Poll Radarr: open an arrival for each new movie in an intake folder, close arrivals of movies
that left it (moved by hand, by another tool, or removed)."""

import logging

from sqlalchemy import select

from triage.core import clock
from triage.core.settings import normalize_folder, same_folder
from triage.domain import arrivals
from triage.models import Arrival, MovieRef
from triage.worker import queue
from triage.worker.requests import look_up_requests
from triage.worker.runner import JobContext

log = logging.getLogger(__name__)


async def poll(ctx: JobContext) -> None:
    radarr = ctx.adapters.radarr
    intake = ctx.settings.radarr.intake_root_folders
    if radarr is None or not intake:
        return
    movies = {m.id: m for m in await radarr.movies()}

    still_open: set[int] = set()
    for arrival in await arrivals.open_arrivals(ctx.db):
        movie = movies.get(arrival.radarr_id)
        if movie is None:
            await arrivals.close(ctx.db, arrival, "removed_from_radarr")
        elif not same_folder(movie.root_folder_path, arrival.intake_path):
            # Triage's own move closes the arrival itself once confirmed.
            if not await arrivals.has_move_in_flight(ctx.db, arrival.id):
                await arrivals.close(ctx.db, arrival, "moved_elsewhere")
        else:
            still_open.add(arrival.radarr_id)

    new = 0
    for movie in movies.values():
        folder = movie.root_folder_path
        if not any(same_folder(folder, i) for i in intake):
            continue
        await arrivals.upsert_movie(ctx.db, movie)
        if movie.id in still_open:
            continue
        arrival = Arrival(
            radarr_id=movie.id,
            intake_path=normalize_folder(folder or ""),
            first_seen_at=clock.now(),
        )
        ctx.db.add(arrival)
        await ctx.db.flush()
        await queue.enqueue(ctx.db, "classify", {"arrival_id": arrival.id})
        new += 1
    if new:
        log.info("new movies in intake", extra={"count": new})
    # the movies Triage already knows (sorted, scanned) learn when Radarr added them — read just now
    for ref in await ctx.db.scalars(select(MovieRef).where(MovieRef.added_at.is_(None))):
        known = movies.get(ref.radarr_id)
        if known is not None and known.added is not None:
            ref.added_at = known.added
    await look_up_requests(ctx)
