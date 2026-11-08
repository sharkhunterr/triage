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
            )
            for r in category.rules
        ),
    )


async def definitions(db: AsyncSession) -> list[CategoryDef]:
    """The categories in force, as the scoring engine and decision snapshots see them."""
    return [to_def(c) for c in await active(db)]
