from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from triage.models.base import Base


class Category(Base):
    """A destination the owner defines: a Radarr root folder and the rules that lead to it."""

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text, default="")
    root_folder_path: Mapped[str | None] = mapped_column(String(500))
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None]

    rules: Mapped[list["Rule"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="Rule.id", lazy="selectin"
    )


class Rule(Base):
    """A condition on one metadata field; its weight goes to its category when it matches."""

    __tablename__ = "rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    field: Mapped[str] = mapped_column(String(32))
    operator: Mapped[str] = mapped_column(String(16), default="is")
    value: Mapped[str] = mapped_column(String(200))
    weight: Mapped[int] = mapped_column(Integer, default=30)
    decisive: Mapped[bool] = mapped_column(Boolean, default=False)
    excludes: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    category: Mapped[Category] = relationship(back_populates="rules")
