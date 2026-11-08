"""The app factory: API under /api/v1, the built frontend at /, the worker in the lifespan."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from triage import __version__
from triage.adapters.factory import AdapterFactory, make_factory
from triage.app.state import AppState
from triage.core.config import RuntimeConfig
from triage.core.db import create_engine, create_session_factory
from triage.core.errors import install_error_handlers
from triage.core.logging import configure_logging
from triage.core.security import LoginThrottle
from triage.worker.jobs import build_worker

API_PREFIX = "/api/v1"


def run_migrations(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("+aiosqlite", ""))
    command.upgrade(config, "head")


async def startup(
    app: FastAPI,
    config: RuntimeConfig,
    adapter_factory: AdapterFactory | None = None,
    *,
    start_worker: bool = True,
    migrate: bool = True,
) -> AppState:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    if migrate:
        await asyncio.to_thread(run_migrations, config.database_url)
    engine = create_engine(config.database_url)
    session_factory = create_session_factory(engine)
    http = httpx.AsyncClient(timeout=30, follow_redirects=True)
    factory = adapter_factory or make_factory(http)
    worker = build_worker(session_factory, factory)
    state = AppState(config, engine, session_factory, factory, worker, http, LoginThrottle())
    app.state.triage = state
    if start_worker:
        worker.start()
    return state


async def shutdown(app: FastAPI) -> None:
    state: AppState = app.state.triage
    await state.worker.stop()
    await state.http.aclose()
    await state.engine.dispose()


def _routers() -> list[APIRouter]:
    from triage.api import auth, categories, decisions, settings

    return [auth.router, categories.router, decisions.router, settings.router]


def create_app(
    config: RuntimeConfig | None = None,
    *,
    adapter_factory: AdapterFactory | None = None,
    start_worker: bool = True,
) -> FastAPI:
    config = config or RuntimeConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        await startup(app, config, adapter_factory, start_worker=start_worker)
        try:
            yield
        finally:
            await shutdown(app)

    app = FastAPI(
        title="Triage",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)
    for router in _routers():
        app.include_router(router, prefix=API_PREFIX)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    _mount_frontend(app, config.static_dir or Path(__file__).resolve().parents[3] / "static")
    return app


def _mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve the built single-page app; unknown paths fall back to index.html."""
    index = static_dir / "index.html"
    if not index.is_file():
        return
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:  # sync: runs in the threadpool (file checks block)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and static_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)
