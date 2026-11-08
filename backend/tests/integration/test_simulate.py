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


async def test_changing_the_tmdb_language_refreshes_the_cached_metadata(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await env.settings(tmdb={"api_key": "k"})
    add_toy_story(env)
    await owner.post("/api/v1/movies/1/simulate")
    await owner.post("/api/v1/movies/1/simulate")
    assert env.fakes.tmdb is not None and env.fakes.tmdb.calls == [862]  # cached
    await env.settings(tmdb={"language": "fr-FR"})
    await owner.post("/api/v1/movies/1/simulate")
    assert env.fakes.tmdb.calls == [862, 862]


async def test_titles_follow_the_tmdb_language(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    assert env.fakes.tmdb is not None
    env.fakes.tmdb.set(862, genres=["Animation"], companies=["Pixar"], title="Toy Story VF")
    await env.state.worker.tick(poll=True)
    (item,) = (await owner.get("/api/v1/decisions")).json()["items"]
    assert item["movie"]["title"] == "Toy Story VF"
    found = (await owner.get("/api/v1/decisions", params={"q": "vf"})).json()["items"]
    assert len(found) == 1


async def test_changing_the_language_retitles_the_history_too(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(tmdb={"api_key": "k"})
    add_toy_story(env)
    await env.state.worker.tick(poll=True)  # moved, with Radarr's title
    assert env.fakes.tmdb is not None
    env.fakes.tmdb.set(862, genres=["Animation"], title="Toy Story (FR)")
    await owner.patch("/api/v1/settings", json={"tmdb": {"language": "fr-FR"}})
    await env.state.worker.tick()
    (item,) = (await owner.get("/api/v1/decisions")).json()["items"]
    assert item["movie"]["title"] == "Toy Story (FR)"


async def test_analyze_a_waiting_movie_now_replaces_its_decision(owner: AsyncClient, env: Env):
    from tests.helpers import add_ambiguous
    from triage.models import Category, Rule

    await seed_categories(env)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    (held,) = await decisions(env)
    assert held.status == "held"
    async with env.state.session_factory() as db:
        animation = (await db.execute(Category.__table__.select().where(Category.key == "animation"))).first()
        assert animation is not None
        db.add(
            Rule(category_id=animation.id, field="company", operator="contains", value="Madhouse", weight=40)
        )
        await db.commit()

    response = await owner.post("/api/v1/movies/3/analyze")
    assert response.status_code == 200, response.text
    fresh = response.json()
    assert fresh["status"] == "proposed" and fresh["source"] == "intake" and fresh["id"] != held.id
    assert [d.status for d in await decisions(env)] == ["superseded", "proposed"]


async def test_analyze_a_movie_outside_the_intake_folder_only_shows_the_result(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    await env.state.worker.tick(poll=True)  # moved to its library
    response = await owner.post("/api/v1/movies/1/analyze")
    assert response.json()["status"] == "simulated"
    assert env.fakes.radarr is not None and len(env.fakes.radarr.moves) == 1
