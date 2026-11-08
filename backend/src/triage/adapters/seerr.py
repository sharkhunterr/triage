"""Overseerr / Jellyseerr: read-only. Triage never edits requests — Seerr refuses edits of
approved requests and re-sends any edited request to Radarr (research R6)."""

from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import SeerrRequest, ServiceCheck

SERVICE = "Seerr"
PAGE = 100
MAX_PAGES = 20
STATUSES = {1: "pending", 2: "approved", 3: "declined", 4: "failed", 5: "completed"}


def parse_request(data: dict[str, Any]) -> SeerrRequest | None:
    media = data.get("media") or {}
    if not media.get("tmdbId"):
        return None
    user = data.get("requestedBy") or {}
    status = data.get("status")
    return SeerrRequest(
        id=int(data["id"]),
        tmdb_id=int(media["tmdbId"]),
        status=STATUSES.get(status, str(status)) if isinstance(status, int) else str(status),
        requested_by=user.get("displayName") or user.get("username") or user.get("email"),
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

    async def request_for(self, tmdb_id: int) -> SeerrRequest | None:
        """The most recent movie request for ``tmdb_id`` (newest pages first)."""
        for page in range(MAX_PAGES):
            data = await self._get(
                "/api/v1/request",
                {
                    "take": PAGE,
                    "skip": page * PAGE,
                    "filter": "all",
                    "sort": "modified",
                    "mediaType": "movie",
                },
            )
            results = (data or {}).get("results") or []
            for item in results:
                request = parse_request(item)
                if request and request.tmdb_id == tmdb_id:
                    return request
            if len(results) < PAGE:
                break
        return None
