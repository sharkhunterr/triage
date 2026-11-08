"""Arrivals: one stay of a movie in an intake folder (research R10)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from triage.adapters.types import RadarrMovie
from triage.core import clock
from triage.core.settings import normalize_folder
from triage.domain import decisions as d
from triage.models import Arrival, Decision, MovieRef


async def upsert_movie(db: AsyncSession, movie: RadarrMovie) -> MovieRef:
    ref = await db.get(MovieRef, movie.id)
    if ref is None:
        ref = MovieRef(radarr_id=movie.id, title=movie.title, updated_at=clock.now())
        db.add(ref)
    ref.tmdb_id = movie.tmdb_id
    ref.title = movie.title
    ref.year = movie.year
    ref.poster_url = movie.poster_url
    ref.root_folder_path = normalize_folder(movie.root_folder_path) if movie.root_folder_path else None
    ref.updated_at = clock.now()
    await db.flush()
    return ref


async def open_arrivals(db: AsyncSession) -> list[Arrival]:
    return list(await db.scalars(select(Arrival).where(Arrival.closed_at.is_(None))))


async def close(db: AsyncSession, arrival: Arrival, reason: str) -> None:
    """Close the arrival; its decisions still waiting for an outcome no longer apply."""
    if arrival.closed_at is not None:
        return
    arrival.closed_at = clock.now()
    arrival.close_reason = reason
    pending = await db.scalars(
        select(Decision).where(
            Decision.arrival_id == arrival.id, Decision.status.in_([d.PROPOSED, d.HELD, d.FAILED])
        )
    )
    for decision in pending:
        await d.transition(db, decision, d.SUPERSEDED)
    await db.flush()


async def has_move_in_flight(db: AsyncSession, arrival_id: int) -> bool:
    return (
        await db.scalar(
            select(Decision.id).where(Decision.arrival_id == arrival_id, Decision.status == d.MOVING).limit(1)
        )
    ) is not None
