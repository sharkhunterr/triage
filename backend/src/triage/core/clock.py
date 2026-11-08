"""The time source. Tests replace ``now`` to move time forward (backoff, expiry)."""

from collections.abc import Callable
from datetime import UTC, datetime


def _system_now() -> datetime:
    return datetime.now(UTC)


_now: Callable[[], datetime] = _system_now


def now() -> datetime:
    return _now()


def set_now(source: Callable[[], datetime] | None) -> None:
    global _now
    _now = source or _system_now
