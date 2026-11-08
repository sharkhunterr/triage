"""Titles in the TMDB language for every known movie (history included), after a language change
or on request. Uses the metadata cache, so a second run costs nothing."""

from sqlalchemy import select

from triage.core.activity import note, step
from triage.domain.classify import tmdb_details
from triage.models import MovieRef, WorkItem
from triage.worker.runner import JobContext


async def refresh_titles_job(ctx: JobContext, item: WorkItem) -> None:
    if ctx.adapters.tmdb is None:
        return
    refs = list(await ctx.db.scalars(select(MovieRef).where(MovieRef.tmdb_id.is_not(None))))
    note(title=ctx.settings.tmdb.language)
    with step("titles") as titles:
        updated = 0
        for ref in refs:
            details = await tmdb_details(ctx.db, ctx.adapters, ref.tmdb_id, ctx.settings.tmdb.language)
            if details is not None and details.title != ref.local_title:
                ref.local_title = details.title
                updated += 1
            await ctx.db.commit()  # one movie at a time: never hold the lock across TMDB calls
        titles.detail = f"{updated} / {len(refs)}"
