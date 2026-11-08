"""Shared seeds for integration tests: the movies/animation categories and typical movies."""

from sqlalchemy import select

from tests.conftest import Env
from triage.core import clock
from triage.models import Arrival, Category, Decision, Rule, WorkItem

ANIMATION_FOLDER = "/media/animation"
FILMS_FOLDER = "/media/films"
INTAKE = "/media/intake"


async def seed_categories(env: Env, *, animation_folder: str | None = ANIMATION_FOLDER) -> None:
    async with env.state.session_factory() as db:
        db.add_all(
            [
                Category(
                    key="animation",
                    name="Dessins animés",
                    description="Animated films for children and families",
                    root_folder_path=animation_folder,
                    position=1,
                    version=1,
                    rules=[
                        Rule(field="genre", operator="is", value="Animation", weight=60),
                        Rule(field="keyword", operator="contains", value="anime", weight=30),
                        Rule(field="company", operator="contains", value="Pixar", weight=40),
                        Rule(field="genre", operator="is", value="Documentary", weight=10, decisive=False),
                    ],
                ),
                Category(
                    key="films",
                    name="Films",
                    description="Live-action films",
                    root_folder_path=FILMS_FOLDER,
                    is_fallback=True,
                    position=2,
                    version=1,
                    rules=[Rule(field="keyword", operator="contains", value="live action", weight=40)],
                ),
            ]
        )
        await db.commit()


def add_toy_story(env: Env, movie_id: int = 1) -> None:
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    env.fakes.radarr.add(movie_id, "Toy Story", genres=["Animation", "Family"], tmdb_id=862)
    env.fakes.tmdb.set(862, genres=["Animation"], companies=["Pixar"], keywords=["computer animation"])


def add_heat(env: Env, movie_id: int = 2) -> None:
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    env.fakes.radarr.add(movie_id, "Heat", genres=["Crime", "Thriller"], tmdb_id=949)
    env.fakes.tmdb.set(949, genres=["Crime", "Thriller"], companies=["Warner Bros. Pictures"])


def add_ambiguous(env: Env, movie_id: int = 3) -> None:
    """Animation genre alone: 60 / (60 + 20) = 0.75, below the 0.80 threshold."""
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    env.fakes.radarr.add(movie_id, "Perfect Blue", genres=["Animation", "Thriller"], tmdb_id=10494)
    env.fakes.tmdb.set(10494, genres=["Animation", "Thriller"], companies=["Madhouse"])


async def decisions(env: Env) -> list[Decision]:
    async with env.state.session_factory() as db:
        return list(await db.scalars(select(Decision).order_by(Decision.id)))


async def arrivals(env: Env) -> list[Arrival]:
    async with env.state.session_factory() as db:
        return list(await db.scalars(select(Arrival).order_by(Arrival.id)))


async def work_items(env: Env, kind: str | None = None) -> list[WorkItem]:
    async with env.state.session_factory() as db:
        query = select(WorkItem).order_by(WorkItem.id)
        if kind:
            query = query.where(WorkItem.kind == kind)
        return list(await db.scalars(query))


async def automatic(env: Env) -> None:
    await env.settings(sorting={"mode": "automatic"})


def now():
    return clock.now()
