"""Radarr API v3. Moving a movie only changes its root folder through the movie editor; the
movie entry is never removed or re-added, so request portals keep tracking it (research R2)."""

from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import RadarrMovie, RootFolder, ServiceCheck, ServiceError

SERVICE = "Radarr"


def parse_movie(data: dict[str, Any]) -> RadarrMovie:
    language = data.get("originalLanguage") or {}
    poster = data.get("remotePoster") or next(
        (i.get("remoteUrl") for i in data.get("images") or [] if i.get("coverType") == "poster"), None
    )
    return RadarrMovie(
        id=int(data["id"]),
        tmdb_id=data.get("tmdbId") or None,
        title=data.get("title") or "?",
        year=data.get("year") or None,
        root_folder_path=data.get("rootFolderPath"),
        genres=tuple(data.get("genres") or ()),
        keywords=tuple(data.get("keywords") or ()),
        studio=data.get("studio") or None,
        certification=data.get("certification") or None,
        original_language=language.get("name") if isinstance(language, dict) else None,
        overview=data.get("overview") or None,
        poster_url=poster,
        has_file=bool(data.get("hasFile")),
    )


class RadarrClient:
    def __init__(self, url: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30)
        self._base = url.rstrip("/")
        self._headers = {"X-Api-Key": api_key}

    async def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        return await request_json(
            self._client, SERVICE, method, f"{self._base}{path}", headers=self._headers, **kwargs
        )

    async def check(self) -> ServiceCheck:
        async def call() -> str:
            status = await self._call("GET", "/api/v3/system/status")
            return f"Radarr {status.get('version', '?')}"

        return await timed_check(SERVICE, call)

    async def root_folders(self) -> list[RootFolder]:
        data = await self._call("GET", "/api/v3/rootfolder")
        return [
            RootFolder(
                path=r["path"], accessible=bool(r.get("accessible", True)), free_space=r.get("freeSpace")
            )
            for r in data or []
        ]

    async def movies(self) -> list[RadarrMovie]:
        return [parse_movie(m) for m in await self._call("GET", "/api/v3/movie") or []]

    async def movie(self, movie_id: int) -> RadarrMovie | None:
        try:
            return parse_movie(await self._call("GET", f"/api/v3/movie/{movie_id}"))
        except ServiceError as exc:
            if exc.message == "not found":
                return None
            raise

    async def move(self, movie_id: int, root_folder_path: str) -> None:
        # Exactly the editor call of Radarr's own "Move to root folder" — never delete anything.
        await self._call(
            "PUT",
            "/api/v3/movie/editor",
            json={
                "movieIds": [movie_id],
                "rootFolderPath": root_folder_path,
                "moveFiles": True,
                "deleteFiles": False,
                "addImportExclusion": False,
            },
        )
