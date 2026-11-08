from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from triage.models.base import Base


class Scan(Base):
    """An owner-started classification of one root folder: proposals only."""

    __tablename__ = "scan"

    id: Mapped[int] = mapped_column(primary_key=True)
    root_folder_path: Mapped[str] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(16), default="running")
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]


class WorkItem(Base):
    """Persistent queue of the in-process worker: survives restarts, retries with backoff."""

    __tablename__ = "work_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    ref: Mapped[dict[str, Any]]
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


class AuditEvent(Base):
    """Append-only trail of every move and owner action (FR-031)."""

    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(index=True)
    actor: Mapped[str] = mapped_column(String(8))
    action: Mapped[str] = mapped_column(String(32))
    radarr_id: Mapped[int | None]
    decision_id: Mapped[int | None]
    from_path: Mapped[str | None] = mapped_column(String(500))
    to_path: Mapped[str | None] = mapped_column(String(500))
    result: Mapped[str] = mapped_column(String(16), default="ok")
    detail: Mapped[str | None] = mapped_column(Text)
