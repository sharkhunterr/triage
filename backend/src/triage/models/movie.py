from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from triage.models.base import Base


class MovieRef(Base):
    """Triage's view of a Radarr movie. Radarr stays the source of truth (Constitution V)."""

    __tablename__ = "movie_ref"

    radarr_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    tmdb_id: Mapped[int | None]
    title: Mapped[str] = mapped_column(String(300))
    # the title in the TMDB language, when TMDB has one; Radarr's own title otherwise
    local_title: Mapped[str | None] = mapped_column(String(300))
    year: Mapped[int | None]
    poster_url: Mapped[str | None] = mapped_column(String(500))
    root_folder_path: Mapped[str | None] = mapped_column(String(500))
    corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime]


class MetadataCache(Base):
    __tablename__ = "metadata_cache"

    tmdb_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    payload: Mapped[dict[str, Any]]
    fetched_at: Mapped[datetime]


class Arrival(Base):
    """One stay of a movie in an intake folder: the unit processed exactly once (research R10)."""

    __tablename__ = "arrival"
    __table_args__ = (
        Index("uq_arrival_open", "radarr_id", unique=True, sqlite_where=text("closed_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    radarr_id: Mapped[int] = mapped_column(ForeignKey("movie_ref.radarr_id"))
    intake_path: Mapped[str] = mapped_column(String(500))
    first_seen_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    close_reason: Mapped[str | None] = mapped_column(String(32))
