from httpx import AsyncClient

from tests.conftest import Env
from tests.helpers import add_ambiguous, add_toy_story, automatic, decisions, seed_categories, work_items

SMTP = {"host": "smtp.test", "sender": "triage@example.org", "recipient": "owner@example.org"}


async def test_a_held_movie_is_never_moved_and_triggers_one_email(env: Env):
    await seed_categories(env)
    await automatic(env)
    await env.settings(smtp=SMTP)
    add_ambiguous(env, 3)
    add_ambiguous(env, 4)
    await env.state.worker.tick(poll=True)

    assert {d.status for d in await decisions(env)} == {"held"}
    assert env.fakes.radarr is not None and env.fakes.radarr.moves == []
    assert env.fakes.mailer is not None
    (message,) = env.fakes.mailer.sent
    assert message.to == "owner@example.org"
    assert "2" in message.subject
    assert message.text.count("Perfect Blue") == 2
    assert "http://triage.test/r/" in message.text
    assert "c=animation" in message.html and "c=films" in message.html and "c=intake" in message.html
    assert all(d.notified_at is not None for d in await decisions(env))

    await env.state.worker.tick(poll=True)
    assert len(env.fakes.mailer.sent) == 1  # never twice for the same movies


async def test_proposals_and_moves_are_not_emailed(env: Env):
    await seed_categories(env)
    await env.settings(smtp=SMTP)
    add_toy_story(env)  # preview mode: a proposal
    await env.state.worker.tick(poll=True)
    assert env.fakes.mailer is not None and env.fakes.mailer.sent == []


async def test_mail_server_down_retries_and_the_review_queue_still_shows_the_movie(
    owner: AsyncClient, env: Env
):
    await seed_categories(env)
    await env.settings(smtp=SMTP)
    add_ambiguous(env)
    assert env.fakes.mailer is not None
    env.fakes.mailer.down = True
    await env.state.worker.tick(poll=True)
    (email,) = await work_items(env, "send_email")
    assert (email.state, email.attempts) == ("pending", 1)
    review = (await owner.get("/api/v1/review")).json()
    assert [d["movie"]["title"] for d in review] == ["Perfect Blue"]

    env.fakes.mailer.down = False
    env.clock.advance(minutes=2)
    await env.state.worker.tick()
    assert len(env.fakes.mailer.sent) == 1


async def test_without_email_settings_nothing_is_sent(env: Env):
    await seed_categories(env)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    assert env.fakes.mailer is not None and env.fakes.mailer.sent == []
    assert await work_items(env, "send_email") == []


async def test_emails_follow_the_owner_language(owner: AsyncClient, env: Env):
    await owner.put("/api/v1/auth/me/locale", json={"locale": "fr"})
    await seed_categories(env)
    await env.settings(smtp=SMTP)
    add_ambiguous(env)
    await env.state.worker.tick(poll=True)
    assert env.fakes.mailer is not None
    (message,) = env.fakes.mailer.sent
    assert "à trancher" in message.subject.lower()
