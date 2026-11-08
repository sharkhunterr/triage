"""Demo mode (``TRIAGE_DEMO=1``): Triage runs against an in-memory Radarr/TMDB library.

Used by the end-to-end tests and to try Triage without connecting anything. Nothing here
reaches the network.
"""

from dataclasses import dataclass, replace

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage.adapters.types import (
    Adapters,
    EmailMessage,
    RadarrMovie,
    RootFolder,
    ServiceCheck,
    ServiceError,
    TmdbDetails,
)
from triage.core.settings import AppSettings, load_settings, save_settings

INTAKE = "/movies/Nouveaux"
FILMS = "/movies/Films"
ANIMATION = "/movies/Dessins animés"


@dataclass(frozen=True)
class Sample:
    id: int
    title: str
    year: int
    folder: str
    genres: tuple[str, ...]
    companies: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    overview: str = ""


SAMPLES = (
    Sample(
        1,
        "Toy Story",
        1995,
        INTAKE,
        ("Animation", "Family", "Comedy"),
        ("Pixar",),
        ("toy", "computer animation"),
        "Woody, a cowboy doll, feels threatened when a new spaceman toy arrives.",
    ),
    Sample(
        2,
        "Heat",
        1995,
        INTAKE,
        ("Crime", "Drama", "Thriller"),
        ("Warner Bros. Pictures",),
        ("heist",),
        "A detective tracks a crew of professional thieves in Los Angeles.",
    ),
    Sample(
        3,
        "Perfect Blue",
        1997,
        INTAKE,
        ("Animation", "Thriller"),
        ("Madhouse",),
        ("psychological thriller",),
        "A pop singer turned actress starts losing her grip on reality.",
    ),
    Sample(
        4,
        "Who Framed Roger Rabbit",
        1988,
        INTAKE,
        ("Animation", "Comedy", "Crime"),
        ("Touchstone Pictures",),
        ("live action and animation",),
        "A detective investigates a murder in a world where cartoons are real.",
    ),
    Sample(
        5,
        "Coco",
        2017,
        INTAKE,
        ("Animation", "Family", "Fantasy"),
        ("Pixar",),
        ("day of the dead",),
        "A boy who dreams of music journeys into the Land of the Dead.",
    ),
    Sample(
        10,
        "Spirited Away",
        2001,
        FILMS,
        ("Animation", "Family", "Fantasy"),
        ("Studio Ghibli",),
        ("anime",),
        "A girl wanders into a world of spirits.",
    ),
    Sample(
        11,
        "Inception",
        2010,
        FILMS,
        ("Action", "Science Fiction"),
        ("Legendary Pictures",),
        ("dream",),
        "A thief enters people's dreams to steal their secrets.",
    ),
    Sample(
        12,
        "Up",
        2009,
        ANIMATION,
        ("Animation", "Adventure"),
        ("Pixar",),
        (),
        "An old man ties balloons to his house and flies away.",
    ),
)


class DemoRadarr:
    def __init__(self) -> None:
        self.folders = [RootFolder(INTAKE), RootFolder(FILMS), RootFolder(ANIMATION)]
        self.library = {
            s.id: RadarrMovie(
                id=s.id,
                tmdb_id=s.id * 100,
                title=s.title,
                year=s.year,
                root_folder_path=s.folder,
                genres=s.genres,
                keywords=s.keywords,
                studio=s.companies[0] if s.companies else None,
                overview=s.overview,
            )
            for s in SAMPLES
        }

    async def check(self) -> ServiceCheck:
        return ServiceCheck(True, "Radarr (demo)")

    async def root_folders(self) -> list[RootFolder]:
        return list(self.folders)

    async def movies(self) -> list[RadarrMovie]:
        return list(self.library.values())

    async def movie(self, movie_id: int) -> RadarrMovie | None:
        return self.library.get(movie_id)

    async def move(self, movie_id: int, root_folder_path: str) -> None:
        if movie_id not in self.library:
            raise ServiceError("Radarr", "not found", retryable=False)
        self.library[movie_id] = replace(self.library[movie_id], root_folder_path=root_folder_path)


class DemoTmdb:
    async def check(self) -> ServiceCheck:
        return ServiceCheck(True, "TMDB (demo)")

    async def details(self, tmdb_id: int) -> TmdbDetails:
        sample = next((s for s in SAMPLES if s.id * 100 == tmdb_id), None)
        if sample is None:
            return TmdbDetails()
        return TmdbDetails(genres=sample.genres, keywords=sample.keywords, companies=sample.companies)


class DemoMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def check(self) -> ServiceCheck:
        return ServiceCheck(True, "Email (demo — not sent)")

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class Demo:
    def __init__(self) -> None:
        self.radarr = DemoRadarr()
        self.tmdb = DemoTmdb()
        self.mailer = DemoMailer()

    def factory(self, settings: AppSettings) -> Adapters:
        return Adapters(
            radarr=self.radarr,
            tmdb=self.tmdb,
            mailer=self.mailer if settings.email_enabled else None,
        )


async def seed_settings(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as db:
        settings = await load_settings(db)
        if settings.radarr_configured:
            return
        settings.radarr.url = "http://radarr.demo"
        settings.radarr.api_key = "demo"
        settings.radarr.intake_root_folders = [INTAKE]
        settings.tmdb.api_key = "demo"
        await save_settings(db, settings)
        await db.commit()
