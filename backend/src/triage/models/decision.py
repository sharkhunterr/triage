from datetime import datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from triage.models.base import Base


class Decision(Base):
    """One classification of one movie, with everything needed to explain it (Constitution III).

    ``signals`` are metadata facts; ``ai`` is the AI's interpretation — kept apart so the
    interface never presents an inference as a fact.
    """

    __tablename__ = "decision"

    id: Mapped[int] = mapped_column(primary_key=True)
    radarr_id: Mapped[int] = mapped_column(ForeignKey("movie_ref.radarr_id"), index=True)
    arrival_id: Mapped[int | None] = mapped_column(ForeignKey("arrival.id"), index=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scan.id"), index=True)
    source: Mapped[str] = mapped_column(String(16))  # intake | scan | simulation | correction
    from_root_folder: Mapped[str | None] = mapped_column(String(500))
    signals: Mapped[list[Any]]
    ai: Mapped[dict[str, Any] | None]
    scores: Mapped[dict[str, Any]]
    reasons: Mapped[list[Any]]
    top_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    categories_snapshot: Mapped[list[Any]]
    status: Mapped[str] = mapped_column(String(16), index=True)
    actor: Mapped[str] = mapped_column(String(8), default="triage")  # triage | owner
    target_category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    target_root_folder: Mapped[str | None] = mapped_column(String(500))
    request_check: Mapped[dict[str, Any] | None]
    error: Mapped[str | None] = mapped_column(Text)
    notified_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(index=True)
    decided_at: Mapped[datetime | None]


class ReviewLink(Base):
    """A one-click choice sent by email: single use, expiring, revoked once the movie is decided."""

    __tablename__ = "review_link"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decision.id", ondelete="CASCADE"), index=True)
    choice: Mapped[str] = mapped_column(String(64))  # category key or "intake"
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
