from httpx import AsyncClient

from tests.conftest import Env
from tests.fakes.ollama import FakeOllama
from tests.helpers import add_ambiguous, add_toy_story, automatic, seed_categories
from triage.adapters.types import AiVerdict


async def test_each_analysis_shows_its_steps_and_outcome(owner: AsyncClient, env: Env):
    await seed_categories(env)
    add_toy_story(env)
    env.fakes.ollama = FakeOllama(AiVerdict("films", 1.0, "never asked"))
    await env.state.worker.tick(poll=True)

    activity = (await owner.get("/api/v1/activity")).json()
    assert activity["running"] is None
    (entry,) = [e for e in activity["recent"] if e["kind"] == "classify"]
    assert entry["title"] == "Toy Story" and entry["outcome"] == "proposed" and entry["decision_id"]
    steps = {s["name"]: s for s in entry["steps"]}
    assert list(steps) == ["radarr", "metadata", "rules", "ai", "decision"]
    assert all(s["state"] in ("done", "skipped") for s in steps.values())
    assert steps["ai"]["state"] == "skipped" and steps["ai"]["detail"] == "rules_sure"
    assert "Dessins animés" in steps["rules"]["detail"]
    assert activity["run"]["done"] >= 1 and activity["run"]["pending"] == 0


async def test_the_ai_step_and_the_move_are_shown(owner: AsyncClient, env: Env):
    await seed_categories(env)
    await automatic(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "animated"))
    await env.state.worker.tick(poll=True)
    recent = (await owner.get("/api/v1/activity")).json()["recent"]
    classify = next(e for e in recent if e["kind"] == "classify")
    ai = next(s for s in classify["steps"] if s["name"] == "ai")
    assert ai["state"] == "done" and "Dessins animés" in ai["detail"]
    move = next(e for e in recent if e["kind"] == "move")
    assert move["title"] == "Perfect Blue" and move["outcome"] == "moved"
    assert [s["name"] for s in move["steps"]] == ["radarr_move", "verify"]


async def test_the_database_stays_writable_while_the_ai_thinks(env: Env):
    """A slow AI call must not hold SQLite's write lock: the web interface keeps working."""
    from sqlalchemy import text

    await seed_categories(env)
    add_ambiguous(env)
    env.fakes.ollama = FakeOllama(AiVerdict("animation", 0.9, "animated"))
    wrote: list[bool] = []

    async def another_writer() -> None:
        async with env.state.session_factory() as db:
            await db.execute(text("PRAGMA busy_timeout=200"))
            await db.execute(text("UPDATE setting SET key = key"))
            await db.commit()
            wrote.append(True)

    env.fakes.ollama.during = another_writer
    await env.state.worker.tick(poll=True)
    assert wrote == [True]
