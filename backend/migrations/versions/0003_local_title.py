"""movie_ref.local_title: the title in the TMDB language

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-08 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movie_ref") as batch:
        batch.add_column(sa.Column("local_title", sa.String(300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("movie_ref") as batch:
        batch.drop_column("local_title")
