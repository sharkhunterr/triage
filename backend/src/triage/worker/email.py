"""One email per processing run listing the movies held for review (FR-018)."""

from datetime import timedelta

from sqlalchemy import select

from triage.adapters.types import EmailMessage
from triage.core import clock
from triage.core.tokens import create_link
from triage.domain import decisions as d
from triage.domain.categories import active
from triage.models import Decision, MovieRef, Owner, WorkItem
from triage.templates.render import Choice, HeldMovie, review_email
from triage.worker import queue
from triage.worker.runner import JobContext


async def _unnotified(ctx: JobContext) -> list[Decision]:
    return list(
        await ctx.db.scalars(
            select(Decision)
            .where(Decision.status == d.HELD, Decision.source == "intake", Decision.notified_at.is_(None))
            .order_by(Decision.id)
        )
    )


async def notify_held(ctx: JobContext) -> None:
    """After each run: queue one email for the newly held movies, if email is set up."""
    if ctx.adapters.mailer is None or not ctx.settings.email_enabled:
        return
    if await queue.has_open(ctx.db, "send_email"):
        return
    held = await _unnotified(ctx)
    if held:
        await queue.enqueue(ctx.db, "send_email", {"decision_ids": [h.id for h in held]})


async def send_email_job(ctx: JobContext, item: WorkItem) -> None:
    assert ctx.adapters.mailer is not None
    ids = set(item.ref.get("decision_ids") or [])
    held = [h for h in await _unnotified(ctx) if h.id in ids]
    if not held:
        return
    owner = await ctx.db.get(Owner, 1)
    locale = owner.locale if owner else "en"
    validity = ctx.settings.sorting.link_validity_days
    choices = [Choice(c.key, c.name) for c in await active(ctx.db) if c.root_folder_path]
    movies = []
    for decision in held:
        ref = await ctx.db.get(MovieRef, decision.radarr_id)
        movies.append(
            HeldMovie(
                title=(ref.local_title or ref.title) if ref else "?",
                year=ref.year if ref else None,
                poster_url=ref.poster_url if ref else None,
                reasons=decision.reasons or [],
                token=await create_link(ctx.db, decision.id, validity),
            )
        )
    base_url = ctx.settings.base_url or "http://localhost:9393"
    subject, text_body, html = review_email(
        locale, base_url, movies, choices, clock.now() + timedelta(days=validity)
    )
    await ctx.adapters.mailer.send(
        EmailMessage(subject=subject, text=text_body, html=html, to=ctx.settings.smtp.recipient)
    )
    for decision in held:
        decision.notified_at = clock.now()
