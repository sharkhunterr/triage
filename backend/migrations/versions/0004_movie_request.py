"""movie_ref: when Radarr added the movie, who asked for it in Seerr and when

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from triage.models.base import UTCDateTime

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movie_ref") as batch:
        batch.add_column(sa.Column("added_at", UTCDateTime(), nullable=True))
        batch.add_column(sa.Column("requested_by", sa.String(200), nullable=True))
        batch.add_column(sa.Column("requested_at", UTCDateTime(), nullable=True))
        batch.add_column(sa.Column("request_checked_at", UTCDateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("movie_ref") as batch:
        for column in ("request_checked_at", "requested_at", "requested_by", "added_at"):
            batch.drop_column(column)
