"""Owner authentication: argon2 passwords, server-side sessions, CSRF header, login throttling."""

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.core.errors import TooManyRequests
from triage.models import AuthSession, Owner

SESSION_COOKIE = "triage_session"
CSRF_HEADER = "X-Triage-CSRF"
SESSION_LIFETIME = timedelta(days=30)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


async def open_session(db: AsyncSession, request: Request) -> str:
    token = new_token()
    now = clock.now()
    db.add(
        AuthSession(
            id_hash=sha256(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + SESSION_LIFETIME,
            user_agent=(request.headers.get("user-agent") or "")[:255],
            ip=request.client.host if request.client else None,
        )
    )
    await db.flush()
    return token


async def close_session(db: AsyncSession, token: str | None) -> None:
    if token and (row := await db.get(AuthSession, sha256(token))):
        await db.delete(row)
        await db.flush()


async def session_is_valid(db: AsyncSession, token: str | None) -> bool:
    """Valid sessions slide: each use pushes the expiry 30 days forward."""
    if not token:
        return False
    row = await db.get(AuthSession, sha256(token))
    now = clock.now()
    if row is None or row.expires_at <= now:
        return False
    row.last_seen_at = now
    row.expires_at = now + SESSION_LIFETIME
    return True


class LoginThrottle:
    """At most ``limit`` failed sign-ins per IP per ``window`` seconds."""

    def __init__(self, limit: int = 5, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        failures = self._failures[key]
        horizon = time.monotonic() - self.window
        while failures and failures[0] < horizon:
            failures.popleft()
        return failures

    def check(self, key: str) -> None:
        if len(self._prune(key)) >= self.limit:
            raise TooManyRequests("Too many failed sign-ins, try again in a minute")

    def failed(self, key: str) -> None:
        self._prune(key).append(time.monotonic())

    def succeeded(self, key: str) -> None:
        self._failures.pop(key, None)


async def owner_exists(db: AsyncSession) -> bool:
    return (await db.get(Owner, 1)) is not None
