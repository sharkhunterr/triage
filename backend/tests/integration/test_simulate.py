from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import FILMS_FOLDER, add_toy_story, automatic, decisions, seed_categories, work_items


async def test_simulate_shows_the_decision_without_acting(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(smtp={"host": "smtp.test", "sender": "t@x", "recipient": "o@x"})
    add_toy_story(env)
    response = await owner.post("/api/v1/movies/1/simulate")
    assert response.status_code == 200
    simulated = response.json()
    assert simulated["status"] == "simulated"
    assert simulated["top_category"]["key"] == "animation"
    assert simulated["signals"]
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []
    assert await work_items(env, "move") == []
    assert env.fakes.mailer is not None and env.fakes.mailer.sent == []


async def test_simulations_stay_out_of_history_and_review(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    await owner.post("/api/v1/movies/1/simulate")
    assert (await owner.get("/api/v1/decisions")).json()["items"] == []
    assert (await owner.get("/api/v1/review")).json() == []
    assert len(await decisions(env)) == 1


async def test_simulate_any_movie_even_outside_intake(owner: AsyncClient, env: Env):
    await seed_categories(env)
    assert env.fakes.radarr is not None
    env.fakes.radarr.add(7, "Heat", folder=FILMS_FOLDER, genres=["Crime"])
    simulated = (await owner.post("/api/v1/movies/7/simulate")).json()
    assert simulated["top_category"]["key"] == "films"


async def test_simulate_unknown_movie(owner: AsyncClient):
    assert (await owner.post("/api/v1/movies/404/simulate")).status_code == 404
