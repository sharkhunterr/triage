"""Wikidata and Wikipedia (when switched on): the kind of work becomes a fact rules can match, the
article's opening goes to the AI and to the sheet; a Wikidata outage never holds the analysis."""

from httpx import AsyncClient

from tests.conftest import Env
from tests.fakes.ollama import FakeOllama
from tests.fakes.wiki import FakeWiki
from tests.helpers import automatic, decisions, seed_categories
from triage.models import Category, Rule

CONCERTS_FOLDER = "/media/concerts"


async def seed_concerts(env: Env) -> None:
    await seed_categories(env)
    async with env.state.session_factory() as db:
        db.add(
            Category(
                key="concerts",
                name="Concerts",
                description="Concert films",
                root_folder_path=CONCERTS_FOLDER,
                position=3,
                version=1,
                rules=[
                    Rule(
                        field="wikidata", operator="contains", value="concert film", weight=90, decisive=True
                    )
                ],
            )
        )
        await db.commit()


def add_stop_making_sense(env: Env) -> None:
    """No genre, no keyword on TMDB: only Wikidata knows it is a concert film."""
    assert env.fakes.radarr is not None and env.fakes.tmdb is not None
    env.fakes.radarr.add(5, "Stop Making Sense", genres=[], tmdb_id=24128)
    env.fakes.tmdb.set(24128, companies=["Talking Heads"], wikidata_id="Q2351784")


async def test_a_wikidata_type_moves_a_movie_tmdb_says_nothing_of(owner: AsyncClient, env: Env):
    env.fakes.wiki = FakeWiki()
    env.fakes.wiki.set(
        "Q2351784",
        "music documentary film",
        "concert film",
        extract="Stop Making Sense is a 1984 concert film.",
    )
    env.fakes.ollama = FakeOllama()
    await env.settings(
        wiki={"enabled": True}, ollama={"url": "http://ollama.test", "model": "m", "ask": "always"}
    )
    await seed_concerts(env)
    await automatic(env)
    add_stop_making_sense(env)
    await env.state.worker.tick(poll=True)

    (decision,) = await decisions(env)
    assert (decision.status, decision.target_root_folder) == ("moved", CONCERTS_FOLDER)
    detail = (await owner.get(f"/api/v1/decisions/{decision.id}")).json()
    assert detail["facts"]["wikidata"] == ["concert film", "music documentary film"]
    assert detail["wikipedia"] == {
        "extract": "Stop Making Sense is a 1984 concert film.",
        "url": "https://en.wikipedia.org/wiki/Q2351784",
    }
    assert any(s["field"] == "wikidata" and s["decisive"] for s in detail["signals"] if s["kind"] == "fact")


async def test_wikidata_is_read_once_then_cached(env: Env):
    env.fakes.wiki = FakeWiki()
    env.fakes.wiki.set("Q2351784", "concert film", extract="A concert film.")
    env.fakes.ollama = FakeOllama()
    await env.settings(ollama={"url": "http://ollama.test", "model": "m", "ask": "always"})
    await seed_concerts(env)
    add_stop_making_sense(env)
    await env.state.worker.tick(poll=True)
    (_, user, _), *_ = env.fakes.ollama.prompts
    assert "Kind of work (Wikidata): concert film" in user
    assert "Wikipedia: A concert film." in user
    assert env.fakes.wiki.calls == ["Q2351784"]


async def test_a_wikidata_outage_never_holds_the_analysis(env: Env):
    env.fakes.wiki = FakeWiki()
    env.fakes.wiki.down = True
    await seed_concerts(env)
    add_stop_making_sense(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status in ("proposed", "held")  # decided on TMDB's facts alone
    assert decision.target_root_folder != CONCERTS_FOLDER
