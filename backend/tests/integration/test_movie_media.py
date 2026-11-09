"""TMDB stills on the movie sheet, to check the TMDB match."""

from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import add_toy_story, seed_categories


async def test_media_shows_tmdb_stills_from_the_cache(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await env.settings(tmdb={"api_key": "k"})
    add_toy_story(env)
    assert env.fakes.tmdb is not None
    env.fakes.tmdb.set(862, genres=["Animation"], images=["/a.jpg", "/b.jpg"])
    await owner.post("/api/v1/movies/1/simulate")
    media = (await owner.get("/api/v1/movies/1/media")).json()
    assert media["images"] == ["/a.jpg", "/b.jpg"]
    assert env.fakes.tmdb.calls == [862]  # read once, by the analysis


async def test_media_without_tmdb_or_unknown_movie_has_no_images(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await owner.post("/api/v1/movies/1/simulate")
    assert (await owner.get("/api/v1/movies/1/media")).json()["images"] == []  # TMDB not configured
    assert (await owner.get("/api/v1/movies/404/media")).json()["images"] == []


async def test_media_survives_a_tmdb_outage(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await owner.post("/api/v1/movies/1/simulate")
    await env.settings(tmdb={"api_key": "k"})
    assert env.fakes.tmdb is not None
    env.fakes.tmdb.down = True
    response = await owner.get("/api/v1/movies/1/media")
    assert response.status_code == 200 and response.json()["images"] == []
