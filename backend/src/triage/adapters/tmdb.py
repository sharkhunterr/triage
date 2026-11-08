"""TMDB API v3: one call per movie for genres, keywords, companies, certifications."""

import asyncio
import time
from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import ServiceCheck, TmdbDetails

SERVICE = "TMDB"
BASE = "https://api.themoviedb.org/3"


def parse_details(data: dict[str, Any]) -> TmdbDetails:
    certifications = sorted(
        {
            rd["certification"]
            for country in (data.get("release_dates") or {}).get("results") or []
            for rd in country.get("release_dates") or []
            if rd.get("certification")
        }
    )
    return TmdbDetails(
        genres=tuple(g["name"] for g in data.get("genres") or [] if g.get("name")),
        keywords=tuple(
            k["name"] for k in (data.get("keywords") or {}).get("keywords") or [] if k.get("name")
        ),
        companies=tuple(c["name"] for c in data.get("production_companies") or [] if c.get("name")),
        certifications=tuple(certifications),
        original_language=data.get("original_language") or None,
        overview=data.get("overview") or None,
    )


class RateLimiter:
    """At most ``rate`` calls per second (TMDB asks for moderation; research R3)."""

    def __init__(self, rate: float) -> None:
        self._interval = 1.0 / rate
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            delay = self._next - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next = max(time.monotonic(), self._next) + self._interval


# Shared by every client instance: adapters are rebuilt for each job, the rate limit is global.
SHARED_LIMITER = RateLimiter(4.0)


class TmdbClient:
    def __init__(
        self, api_key: str, client: httpx.AsyncClient | None = None, limiter: RateLimiter | None = None
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=20)
        # A v4 read access token (long JWT) goes in the header; a v3 key in the query string.
        if api_key.count(".") == 2:
            self._auth: dict[str, Any] = {"headers": {"Authorization": f"Bearer {api_key}"}}
        else:
            self._auth = {"params": {"api_key": api_key}}
        self._limiter = limiter or SHARED_LIMITER

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        await self._limiter.wait()
        kwargs: dict[str, Any] = {k: dict(v) for k, v in self._auth.items()}
        kwargs.setdefault("params", {}).update(params or {})
        return await request_json(self._client, SERVICE, "GET", f"{BASE}{path}", **kwargs)

    async def check(self) -> ServiceCheck:
        async def call() -> str:
            await self._get("/configuration")
            return "TMDB reachable"

        return await timed_check(SERVICE, call)

    async def details(self, tmdb_id: int) -> TmdbDetails:
        return parse_details(
            await self._get(f"/movie/{tmdb_id}", {"append_to_response": "keywords,release_dates"})
        )
