"""Overseerr / Jellyseerr: read-only. Triage never edits requests — Seerr refuses edits of
approved requests and re-sends any edited request to Radarr (research R6)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx

from triage.adapters.http import parse_time, request_json, timed_check
from triage.adapters.types import SeerrRequest, ServiceCheck

SERVICE = "Seerr"
PAGE = 100
MAX_PAGES = 20
_EPOCH = datetime.min.replace(tzinfo=UTC)
STATUSES = {1: "pending", 2: "approved", 3: "declined", 4: "failed", 5: "completed"}


def parse_request(data: dict[str, Any]) -> SeerrRequest | None:
    """A movie request — a series' is none: its TMDB id may be a movie's too."""
    media = data.get("media") or {}
    if not media.get("tmdbId") or (data.get("type") or media.get("mediaType") or "movie") != "movie":
        return None
    user = data.get("requestedBy") or {}
    status = data.get("status")
    return SeerrRequest(
        id=int(data["id"]),
        tmdb_id=int(media["tmdbId"]),
        status=STATUSES.get(status, str(status)) if isinstance(status, int) else str(status),
        requested_by=user.get("displayName") or user.get("username") or user.get("email"),
        requested_at=parse_time(data.get("createdAt")),
    )


class SeerrClient:
    def __init__(self, url: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=20)
        self._base = url.rstrip("/")
        self._headers = {"X-Api-Key": api_key}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await request_json(
            self._client, SERVICE, "GET", f"{self._base}{path}", headers=self._headers, params=params
        )

    async def check(self) -> ServiceCheck:
        async def call() -> str:
            status = await self._get("/api/v1/status")
            return f"Seerr {status.get('version', '?')}"

        return await timed_check(SERVICE, call)

    async def _requests(self) -> AsyncIterator[SeerrRequest]:
        """Every movie request, the most recently modified first. Only the parameters every Seerr
        knows: Overseerr refuses an unknown one (``mediaType`` is Jellyseerr's) with HTTP 400."""
        for page in range(MAX_PAGES):
            data = await self._get(
                "/api/v1/request",
                {"take": PAGE, "skip": page * PAGE, "filter": "all", "sort": "modified"},
            )
            results = (data or {}).get("results") or []
            for item in results:
                request = parse_request(item)
                if request is not None:
                    yield request
            if len(results) < PAGE:
                break

    async def request_for(self, tmdb_id: int) -> SeerrRequest | None:
        """The most recent movie request for ``tmdb_id`` (newest pages first)."""
        async for request in self._requests():
            if request.tmdb_id == tmdb_id:
                return request
        return None

    async def movie_requests(self) -> dict[int, SeerrRequest]:
        """Each requested movie's latest request, by TMDB id — read in one pass."""
        latest: dict[int, SeerrRequest] = {}
        async for request in self._requests():
            known = latest.get(request.tmdb_id)
            if known is None or (request.requested_at or _EPOCH) > (known.requested_at or _EPOCH):
                latest[request.tmdb_id] = request
        return latest
