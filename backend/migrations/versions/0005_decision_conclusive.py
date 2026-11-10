"""decision: whether the analysis was sure enough to sort the movie on its own

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-10 06:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("decision") as batch:
        batch.add_column(sa.Column("conclusive", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("decision") as batch:
        batch.drop_column("conclusive")
