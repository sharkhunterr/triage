from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tests.fakes import Fakes
from triage.app.main import create_app, shutdown, startup
from triage.app.state import AppState
from triage.core import clock
from triage.core.config import RuntimeConfig
from triage.core.settings import load_settings, save_settings
from triage.models import Base

PASSWORD = "correct horse battery"


class FrozenClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@dataclass
class Env:
    app: FastAPI
    state: AppState
    fakes: Fakes
    clock: FrozenClock

    async def settings(self, **sections: dict[str, object]) -> None:
        """Update stored settings, e.g. ``await env.settings(sorting={"mode": "automatic"})``."""
        async with self.state.session_factory() as db:
            current = await load_settings(db)
            data = current.model_dump()
            for section, values in sections.items():
                if isinstance(data.get(section), dict):
                    data[section].update(values)
                else:
                    data[section] = values
            await save_settings(db, type(current).model_validate(data))
            await db.commit()


@pytest.fixture
def frozen_clock() -> Iterator[FrozenClock]:
    fake = FrozenClock()
    clock.set_now(fake)
    yield fake
    clock.set_now(None)


@pytest.fixture
async def env(tmp_path: Path, frozen_clock: FrozenClock) -> AsyncIterator[Env]:
    config = RuntimeConfig(data_dir=tmp_path, static_dir=tmp_path / "no-static", log_level="WARNING")
    fakes = Fakes()
    app = create_app(config, adapter_factory=fakes.factory, start_worker=False)
    state = await startup(app, config, fakes.factory, start_worker=False, migrate=False)
    async with state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    environment = Env(app, state, fakes, frozen_clock)
    await environment.settings(
        radarr={"url": "http://radarr.test", "api_key": "k", "intake_root_folders": ["/media/intake"]},
        base_url="http://triage.test",
    )
    yield environment
    await shutdown(app)


@pytest.fixture
async def client(env: Env) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=env.app)
    async with AsyncClient(
        transport=transport, base_url="http://triage.test", headers={"X-Triage-CSRF": "1"}
    ) as c:
        yield c


@pytest.fixture
async def owner(client: AsyncClient) -> AsyncClient:
    """A client signed in as the owner."""
    response = await client.post(
        "/api/v1/setup", json={"username": "owner", "password": PASSWORD, "locale": "en"}
    )
    assert response.status_code == 204, response.text
    return client
