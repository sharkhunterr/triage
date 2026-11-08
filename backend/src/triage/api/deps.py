"""FastAPI dependencies: database session, settings, adapters, owner guard."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from triage.adapters.types import Adapters
from triage.app.state import AppState
from triage.core.errors import Forbidden, Unauthorized
from triage.core.security import CSRF_HEADER, SAFE_METHODS, SESSION_COOKIE, session_is_valid
from triage.core.settings import AppSettings, load_settings


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.triage
    return state


async def get_db(state: Annotated[AppState, Depends(get_state)]) -> AsyncIterator[AsyncSession]:
    async with state.session_factory() as session:
        yield session


Db = Annotated[AsyncSession, Depends(get_db)]
State = Annotated[AppState, Depends(get_state)]


async def get_settings(db: Db) -> AppSettings:
    return await load_settings(db)


Settings = Annotated[AppSettings, Depends(get_settings)]


def get_adapters(state: State, settings: Settings) -> Adapters:
    return state.adapter_factory(settings)


AdaptersDep = Annotated[Adapters, Depends(get_adapters)]


async def require_owner(request: Request, db: Db) -> None:
    """Session required everywhere; writes also need the CSRF header (Constitution VII)."""
    if not await session_is_valid(db, request.cookies.get(SESSION_COOKIE)):
        raise Unauthorized("Sign in first")
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise Forbidden("Missing CSRF header", code="csrf")
    await db.commit()


Owner = Depends(require_owner)
