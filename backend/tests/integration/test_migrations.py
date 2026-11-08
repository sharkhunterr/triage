"""The Alembic migrations build exactly the schema the models describe."""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from triage.app.main import run_migrations
from triage.models import Base


def test_migrations_match_the_models(tmp_path: Path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'm.db'}"
    run_migrations(url)
    engine = create_engine(url.replace("+aiosqlite", ""))
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []
