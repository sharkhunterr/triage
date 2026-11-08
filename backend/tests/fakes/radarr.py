from dataclasses import replace
from typing import Any

from triage.adapters.types import RadarrMovie, RootFolder, ServiceCheck, ServiceError


class FakeRadarr:
    """A Radarr library in memory. Records every call so tests can prove what never happened
    (no delete, no re-add)."""

    def __init__(self, root_folders: list[str] | None = None) -> None:
        self.folders = [
            RootFolder(path=p)
            for p in (root_folders or ["/media/intake", "/media/films", "/media/animation"])
        ]
        self.library: dict[int, RadarrMovie] = {}
        self.calls: list[tuple[str, Any]] = []
        self.down = False
        self.ignore_moves = False

    def add(self, movie_id: int, title: str, folder: str = "/media/intake", **fields: Any) -> RadarrMovie:
        movie = RadarrMovie(
            id=movie_id,
            tmdb_id=fields.pop("tmdb_id", movie_id * 10),
            title=title,
            year=fields.pop("year", 2000),
            root_folder_path=folder,
            **{k: tuple(v) if isinstance(v, list) else v for k, v in fields.items()},
        )
        self.library[movie_id] = movie
        return movie

    def _guard(self, call: str, arg: Any = None) -> None:
        self.calls.append((call, arg))
        if self.down:
            raise ServiceError("Radarr", "unreachable (ConnectError)")

    async def check(self) -> ServiceCheck:
        if self.down:
            return ServiceCheck(False, "unreachable (ConnectError)")
        return ServiceCheck(True, "Radarr 6.2.1")

    async def root_folders(self) -> list[RootFolder]:
        self._guard("root_folders")
        return list(self.folders)

    async def movies(self) -> list[RadarrMovie]:
        self._guard("movies")
        return list(self.library.values())

    async def movie(self, movie_id: int) -> RadarrMovie | None:
        self._guard("movie", movie_id)
        return self.library.get(movie_id)

    async def move(self, movie_id: int, root_folder_path: str) -> None:
        self._guard(
            "move", {"movieIds": [movie_id], "rootFolderPath": root_folder_path, "deleteFiles": False}
        )
        if movie_id not in self.library:
            raise ServiceError("Radarr", "not found", retryable=False)
        if not self.ignore_moves:
            self.library[movie_id] = replace(self.library[movie_id], root_folder_path=root_folder_path)

    @property
    def moves(self) -> list[dict[str, Any]]:
        return [arg for call, arg in self.calls if call == "move"]
