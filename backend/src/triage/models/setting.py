from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from triage.models.base import Base


class Setting(Base):
    """The owner's settings, one JSON document per key (``app``). Secrets included: they never
    leave the server (``core.settings`` serializes them as ``{"set": bool}``)."""

    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]]
