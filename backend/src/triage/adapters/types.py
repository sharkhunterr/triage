"""What Triage needs from each external service, independent of how it is reached.

Real clients live next to this module; tests use fakes with the same methods
(Constitution VIII). Only the calls listed in contracts/external-services.md exist here.
"""

from dataclasses import dataclass, field
from typing import Protocol


class ServiceError(Exception):
    """A call to an external service failed. ``retryable`` is false for errors that will not
    fix themselves (bad API key, unknown movie)."""

    def __init__(self, service: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class RootFolder:
    path: str
    accessible: bool = True
    free_space: int | None = None


@dataclass(frozen=True)
class RadarrMovie:
    id: int
    tmdb_id: int | None
    title: str
    year: int | None
    root_folder_path: str | None
    genres: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    studio: str | None = None
    certification: str | None = None
    original_language: str | None = None
    overview: str | None = None
    poster_url: str | None = None
    has_file: bool = False


@dataclass(frozen=True)
class TmdbDetails:
    genres: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    companies: tuple[str, ...] = ()
    certifications: tuple[str, ...] = ()
    original_language: str | None = None
    overview: str | None = None


@dataclass(frozen=True)
class AiVerdict:
    category: str  # a category key, or "unsure"
    confidence: float
    reasoning: str
    duration_ms: int = 0


@dataclass(frozen=True)
class SeerrRequest:
    id: int
    tmdb_id: int
    status: str
    requested_by: str | None = None


@dataclass(frozen=True)
class EmailMessage:
    subject: str
    text: str
    html: str
    to: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceCheck:
    ok: bool
    detail: str
    latency_ms: int = 0


class Radarr(Protocol):
    async def check(self) -> ServiceCheck: ...
    async def root_folders(self) -> list[RootFolder]: ...
    async def movies(self) -> list[RadarrMovie]: ...
    async def movie(self, movie_id: int) -> RadarrMovie | None: ...
    async def move(self, movie_id: int, root_folder_path: str) -> None: ...


class Tmdb(Protocol):
    async def check(self) -> ServiceCheck: ...
    async def details(self, tmdb_id: int) -> TmdbDetails: ...


class Ollama(Protocol):
    async def check(self) -> ServiceCheck: ...
    async def models(self) -> list[str]: ...
    async def classify(self, system: str, user: str, category_keys: list[str]) -> AiVerdict: ...


class Seerr(Protocol):
    async def check(self) -> ServiceCheck: ...
    async def request_for(self, tmdb_id: int) -> SeerrRequest | None: ...


class Mailer(Protocol):
    async def check(self) -> ServiceCheck: ...
    async def send(self, message: EmailMessage) -> None: ...


@dataclass
class Adapters:
    """The services available for one unit of work, built from the current settings.
    Optional services are ``None`` when not configured."""

    radarr: Radarr | None = None
    tmdb: Tmdb | None = None
    ollama: Ollama | None = None
    seerr: Seerr | None = None
    mailer: Mailer | None = None
