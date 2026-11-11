from tests.conftest import Env
from tests.fakes.ollama import FakeOllama
from tests.helpers import (
    ANIMATION_FOLDER,
    add_ambiguous,
    add_toy_story,
    automatic,
    decisions,
    seed_categories,
)
from triage.adapters.types import AiVerdict, ServiceError
from triage.models import Category, Rule


async def test_the_ai_settles_an_ambiguous_movie(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "An animated psychological thriller"))
    await env.state.worker.tick(poll=True)

    (decision,) = await decisions(env)
    assert (decision.status, decision.target_root_folder) == ("moved", ANIMATION_FOLDER)
    assert decision.ai is not None
    assert decision.ai["category"] == "animation" and decision.ai["reasoning"]
    (system, user, keys) = env.fakes.ollama.prompts[0]
    assert keys == ["animation", "films"]
    assert "Animated films for children and families" in system
    assert "Perfect Blue" in user


async def test_an_ai_outage_falls_back_to_the_rules_and_holds(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama()
    env.fakes.ollama.error = ServiceError("Ollama", "timed out")
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert decision.ai == {"error": "timed out", "asked": "unsure"}
    assert {"code": "ai_unavailable", "error": "timed out"} in decision.reasons
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []


async def test_an_unsure_ai_holds(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("unsure", 0.3, "Hard to tell"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert {"code": "ai_unsure"} in decision.reasons


async def test_the_ai_is_not_asked_when_rules_are_conclusive(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_toy_story(env)
    env.fakes.ollama = FakeOllama(AiVerdict("films", 1.0, "wrong"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved" and decision.ai is None
    assert env.fakes.ollama.prompts == []


async def test_the_ai_is_not_asked_when_a_decisive_rule_matched(env: Env):
    await seed_categories(env)
    async with env.state.session_factory() as db:
        db.add(
            Category(
                key="docs",
                name="Docs",
                description="",
                root_folder_path="/media/films",
                position=3,
                version=1,
                rules=[Rule(field="genre", operator="is", value="Thriller", weight=5, decisive=True)],
            )
        )
        await db.commit()
    await automatic(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 1.0, "animated"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved"
    assert env.fakes.ollama.prompts == []


async def test_without_ai_an_ambiguous_movie_is_held(env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"
    assert decision.reasons[0]["code"] == "low_confidence"


async def test_always_asks_the_ai_for_a_second_opinion_even_when_the_rules_agree(env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(ollama={"ask": "always"})
    add_toy_story(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "A Pixar film"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved"
    assert decision.ai is not None and decision.ai["asked"] == "always"
    assert len(env.fakes.ollama.prompts) == 1


async def test_a_disagreeing_second_opinion_holds_the_movie(env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(ollama={"ask": "always"}, sorting={"ai_weight": 100})
    add_toy_story(env)
    env.fakes.ollama = FakeOllama(AiVerdict("films", 1.0, "Looks live action"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held"


async def test_an_ai_outage_does_not_block_a_move_the_rules_are_sure_of(env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(ollama={"ask": "always"})
    add_toy_story(env)
    env.fakes.ollama = FakeOllama()
    env.fakes.ollama.error = ServiceError("Ollama", "timed out")
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "moved"
    assert decision.ai is not None and decision.ai["error"] == "timed out"


async def test_never_asks_the_ai(env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(ollama={"ask": "never"})
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "animated"))
    await env.state.worker.tick(poll=True)
    (decision,) = await decisions(env)
    assert decision.status == "held" and decision.ai is None
    assert env.fakes.ollama.prompts == []


async def test_an_address_without_a_model_never_asks_the_ai(env: Env):
    """The address alone lets the settings test it and list its models; the AI waits for a model."""
    await seed_categories(env)
    await env.settings(ollama={"url": "http://ollama.test", "model": ""})
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "animated"))
    await env.state.worker.tick(poll=True)
    assert env.fakes.ollama.prompts == []
    (decision,) = await decisions(env)
    assert decision.status == "held"
