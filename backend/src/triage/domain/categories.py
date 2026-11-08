"""Categories are configuration (Constitution II): created, edited, and snapshotted here."""

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from triage.domain.scoring import CategoryDef, RuleDef
from triage.models import Category


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "category"


async def unique_key(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    taken = set(await db.scalars(select(Category.key)))
    key, n = base, 2
    while key in taken:
        key, n = f"{base}-{n}", n + 1
    return key


async def active(db: AsyncSession) -> list[Category]:
    return list(
        await db.scalars(
            select(Category).where(Category.deleted_at.is_(None)).order_by(Category.position, Category.id)
        )
    )


def to_def(category: Category) -> CategoryDef:
    return CategoryDef(
        id=category.id,
        key=category.key,
        name=category.name,
        description=category.description,
        root_folder_path=category.root_folder_path,
        is_fallback=category.is_fallback,
        version=category.version,
        rules=tuple(
            RuleDef(
                id=r.id,
                field=r.field,
                operator=r.operator,
                value=r.value,
                weight=r.weight,
                decisive=r.decisive,
                excludes=r.excludes,
            )
            for r in category.rules
        ),
    )


async def definitions(db: AsyncSession) -> list[CategoryDef]:
    """The categories in force, as the scoring engine and decision snapshots see them."""
    return [to_def(c) for c in await active(db)]


CONFIG_REASONS = {"no_categories", "category_without_folder"}


SCOPES = ("all", "waiting", "new")


async def reanalyze(db: AsyncSession, scope: str = "all", *, dry_run: bool = False) -> dict[str, int]:
    """Classify movies of the intake folder again, with today's rules and settings.

    - ``waiting``: held or proposed; the old decision is superseded, never deleted.
    - ``new``: never analysed (an arrival without a decision), or put back in the intake folder by
      a correction (that stay counted as decided; they will only ever be proposed).
    - ``all``: both.
    Returns how many movies each scope covers, and ``count`` for the chosen one.
    """
    from triage.domain import decisions as d
    from triage.models import Arrival, Decision
    from triage.worker import queue

    waiting = list(
        await db.scalars(
            select(Decision).where(
                Decision.status.in_([d.HELD, d.PROPOSED]),
                Decision.source == "intake",
                Decision.actor == "triage",
                Decision.arrival_id.is_not(None),
            )
        )
    )
    put_back = list(
        await db.scalars(
            select(Decision)
            .join(Arrival, Arrival.id == Decision.arrival_id)
            .where(
                Decision.source == "correction",
                Decision.status == d.MOVED,
                Arrival.closed_at.is_(None),
            )
        )
    )
    decided = select(Decision.arrival_id).where(Decision.arrival_id.is_not(None))
    never = [
        a
        for a in await db.scalars(
            select(Arrival).where(Arrival.closed_at.is_(None), Arrival.id.not_in(decided))
        )
        if not await queue.has_open(db, "classify", arrival_id=a.id)
    ]
    counts = {
        "waiting": len(waiting),
        "new": len(put_back) + len(never),
        "all": len(waiting) + len(put_back) + len(never),
    }
    counts["count"] = counts[scope]
    if dry_run:
        return counts
    if scope in ("all", "waiting"):
        for decision in waiting:
            await d.transition(db, decision, d.SUPERSEDED)
            await queue.enqueue(db, "classify", {"arrival_id": decision.arrival_id})
    if scope in ("all", "new"):
        for decision in put_back:
            arrival_id = decision.arrival_id
            decision.arrival_id = None  # the correction stays in the history; the stay is open again
            await queue.enqueue(db, "classify", {"arrival_id": arrival_id})
        for arrival in never:
            await queue.enqueue(db, "classify", {"arrival_id": arrival.id})
    return counts


async def reclassify_config_holds(db: AsyncSession) -> int:
    """Movies held only because of the configuration (no category yet, a category without a
    library) are classified again after categories change. Held for doubt: left alone."""
    from triage.domain import decisions as d
    from triage.models import Decision
    from triage.worker import queue

    held = await db.scalars(
        select(Decision).where(
            Decision.status.in_([d.HELD, d.PROPOSED]),
            Decision.source == "intake",
            Decision.actor == "triage",
            Decision.arrival_id.is_not(None),
        )
    )
    count = 0
    for decision in held:
        if not any(r.get("code") in CONFIG_REASONS for r in decision.reasons or []):
            continue
        await d.transition(db, decision, d.SUPERSEDED)
        await queue.enqueue(db, "classify", {"arrival_id": decision.arrival_id})
        count += 1
    return count
