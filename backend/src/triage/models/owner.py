from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from triage.models.base import Base


class Owner(Base):
    """The one account allowed to sign in."""

    __tablename__ = "owner"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    locale: Mapped[str] = mapped_column(String(5), default="en")
    created_at: Mapped[datetime]


class AuthSession(Base):
    """A signed-in browser. The cookie holds a random value; only its hash is stored."""

    __tablename__ = "session"

    id_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
