"""SQLite through SQLAlchemy async: one engine per process, WAL and foreign keys on."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(url: str) -> AsyncEngine:
    engine = create_async_engine(url, connect_args={"timeout": 30})

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")  # safe with WAL; avoids an fsync per commit
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
