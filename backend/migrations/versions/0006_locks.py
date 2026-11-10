"""movie locks: the library the owner chose by hand; scans respect them or not

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-10 21:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from triage.models.base import UTCDateTime

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("movie_ref") as batch:
        batch.add_column(sa.Column("locked_folder", sa.String(500), nullable=True))
        batch.add_column(sa.Column("locked_via", sa.String(16), nullable=True))
        batch.add_column(sa.Column("locked_at", UTCDateTime(), nullable=True))
    with op.batch_alter_table("scan") as batch:
        batch.add_column(sa.Column("respect_locks", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("scan") as batch:
        batch.drop_column("respect_locks")
    with op.batch_alter_table("movie_ref") as batch:
        batch.drop_column("locked_at")
        batch.drop_column("locked_via")
        batch.drop_column("locked_folder")
