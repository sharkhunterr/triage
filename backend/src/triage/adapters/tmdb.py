"""TMDB API v3: one call per movie for genres, keywords, companies, certifications.

The movie is read in English, the language rules are written in (genres, keywords). The configured
language only picks the synopsis translation and the country whose age ratings are kept."""

import asyncio
import time
from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import ServiceCheck, TmdbDetails

SERVICE = "TMDB"
BASE = "https://api.themoviedb.org/3"


def _certifications(data: dict[str, Any], country: str) -> list[str]:
    return sorted(
        {
            rd["certification"]
            for entry in (data.get("release_dates") or {}).get("results") or []
            if entry.get("iso_3166_1") == country
            for rd in entry.get("release_dates") or []
            if rd.get("certification")
        }
    )


def _translated(data: dict[str, Any], language: str, country: str, key: str) -> str | None:
    """A translated field (overview, title): the country's own translation when there is one, even
    with that field empty (TMDB leaves the title empty when it equals the original: "Toy Story" in
    France must not become Quebec's "Histoire de jouets"); otherwise any of the language."""
    translations = [
        t
        for t in (data.get("translations") or {}).get("translations") or []
        if t.get("iso_639_1") == language
    ]
    own = next((t for t in translations if t.get("iso_3166_1") == country), None)
    if own is not None:
        value = (own.get("data") or {}).get(key)
        return str(value) if value else None
    other = next((t for t in translations if (t.get("data") or {}).get(key)), None)
    return str(other["data"][key]) if other else None


def parse_details(data: dict[str, Any], language: str = "en-US") -> TmdbDetails:
    lang, _, country = language.partition("-")
    # the country's ratings, else the US ones (TMDB's most complete)
    certifications = _certifications(data, country) or _certifications(data, "US")
    return TmdbDetails(
        genres=tuple(g["name"] for g in data.get("genres") or [] if g.get("name")),
        keywords=tuple(
            k["name"] for k in (data.get("keywords") or {}).get("keywords") or [] if k.get("name")
        ),
        companies=tuple(c["name"] for c in data.get("production_companies") or [] if c.get("name")),
        certifications=tuple(certifications),
        original_language=data.get("original_language") or None,
        overview=_translated(data, lang, country, "overview") or data.get("overview") or None,
        title=_translated(data, lang, country, "title"),
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
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        limiter: RateLimiter | None = None,
        language: str = "en-US",
    ) -> None:
        self._language = language
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
        data = await self._get(
            f"/movie/{tmdb_id}", {"append_to_response": "keywords,release_dates,translations"}
        )
        return parse_details(data, self._language)
