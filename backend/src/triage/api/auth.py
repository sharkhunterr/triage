"""First-start setup and owner sign-in (contracts/http-api.md — Auth & setup)."""

from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from triage.api.deps import Db, Owner, State
from triage.core import clock
from triage.core.errors import Conflict, Unauthorized
from triage.core.security import (
    SESSION_COOKIE,
    SESSION_LIFETIME,
    close_session,
    hash_password,
    open_session,
    owner_exists,
    verify_password,
)
from triage.core.settings import load_settings, save_settings
from triage.models import Owner as OwnerRow

router = APIRouter(tags=["auth"])


class SetupStatus(BaseModel):
    needs_setup: bool


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=200)


class SetupBody(Credentials):
    locale: Literal["en", "fr"] = "en"


class Me(BaseModel):
    username: str
    locale: str


def _set_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )


@router.get("/setup/status", response_model=SetupStatus)
async def setup_status(db: Db) -> SetupStatus:
    return SetupStatus(needs_setup=not await owner_exists(db))


@router.post("/setup", status_code=204)
async def setup(body: SetupBody, request: Request, response: Response, db: Db) -> None:
    if await owner_exists(db):
        raise Conflict("Triage is already set up", code="already_set_up")
    db.add(
        OwnerRow(
            id=1,
            username=body.username.strip(),
            password_hash=hash_password(body.password),
            locale=body.locale,
            created_at=clock.now(),
        )
    )
    settings = await load_settings(db)
    if not settings.base_url:
        settings.base_url = str(request.base_url).rstrip("/")
    if body.locale == "fr" and settings.tmdb.language == "en-US":
        settings.tmdb.language = "fr-FR"
    await save_settings(db, settings)
    token = await open_session(db, request)
    await db.commit()
    _set_cookie(request, response, token)


@router.post("/auth/login", status_code=204)
async def login(body: Credentials, request: Request, response: Response, db: Db, state: State) -> None:
    key = request.client.host if request.client else "unknown"
    state.throttle.check(key)
    owner = await db.get(OwnerRow, 1)
    if (
        owner is None
        or owner.username != body.username.strip()
        or not verify_password(owner.password_hash, body.password)
    ):
        state.throttle.failed(key)
        raise Unauthorized("Wrong username or password", code="bad_credentials")
    state.throttle.succeeded(key)
    token = await open_session(db, request)
    await db.commit()
    _set_cookie(request, response, token)


@router.post("/auth/logout", status_code=204, dependencies=[Owner])
async def logout(request: Request, response: Response, db: Db) -> None:
    await close_session(db, request.cookies.get(SESSION_COOKIE))
    await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/auth/me", response_model=Me, dependencies=[Owner])
async def me(db: Db) -> Me:
    owner = await db.get(OwnerRow, 1)
    assert owner is not None
    return Me(username=owner.username, locale=owner.locale)


class LocaleBody(BaseModel):
    locale: Literal["en", "fr"]


@router.put("/auth/me/locale", status_code=204, dependencies=[Owner])
async def set_locale(body: LocaleBody, db: Db) -> None:
    owner = await db.get(OwnerRow, 1)
    assert owner is not None
    owner.locale = body.locale
    await db.commit()
