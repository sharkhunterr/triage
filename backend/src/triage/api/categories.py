"""Categories and presets (contracts/http-api.md — Categories)."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select

from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core import clock
from triage.core.errors import Conflict, NotFound, TriageError
from triage.core.settings import AppSettings, normalize_folder, same_folder
from triage.domain import categories as domain
from triage.domain.presets import PRESETS
from triage.models import Category, Rule
from triage.models import Owner as OwnerRow

router = APIRouter(tags=["categories"], dependencies=[Owner])

FieldName = Literal["genre", "keyword", "company", "certification", "original_language"]
Operator = Literal["is", "contains", "is_not"]


class RuleIn(BaseModel):
    field: FieldName
    operator: Operator = "is"
    value: str = Field(min_length=1, max_length=200)
    weight: int = Field(30, ge=1, le=100)
    decisive: bool = False
    # rules the category out when it matches (its weight is then unused)
    excludes: bool = False

    @model_validator(mode="after")
    def _one_effect(self) -> "RuleIn":
        if self.excludes and self.decisive:
            raise ValueError("A rule cannot be both decisive and excluding")
        return self


class RuleOut(RuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str = Field("", max_length=1000)
    root_folder_path: str | None = None
    is_fallback: bool = False
    rules: list[RuleIn] = Field(default_factory=list, max_length=100)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return value.strip()

    @field_validator("root_folder_path")
    @classmethod
    def _folder(cls, value: str | None) -> str | None:
        return normalize_folder(value) if value and value.strip() else None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    description: str
    root_folder_path: str | None
    is_fallback: bool
    position: int
    version: int
    rules: list[RuleOut]


class ReorderBody(BaseModel):
    ids: list[int]


class PresetCategoryOut(BaseModel):
    name: str
    description: str
    is_fallback: bool
    rule_count: int


class PresetOut(BaseModel):
    key: str
    name: str
    description: str
    categories: list[PresetCategoryOut]


class InvalidFolder(TriageError):
    status_code = 422


async def _validate_folder(path: str | None, settings: AppSettings, adapters: AdaptersDep) -> None:
    if path is None:
        return
    if any(same_folder(path, intake) for intake in settings.radarr.intake_root_folders):
        raise InvalidFolder("An intake folder cannot be a category's library", code="intake_folder")
    if adapters.radarr is None:
        return
    folders = [f.path for f in await adapters.radarr.root_folders()]
    if not any(same_folder(path, f) for f in folders):
        raise InvalidFolder(
            "This folder is not one of Radarr's root folders",
            code="unknown_root_folder",
            details={"path": path},
        )


async def _check_name(db: Db, name: str, exclude_id: int | None = None) -> None:
    clash = await db.scalar(
        select(Category.id).where(
            func.lower(Category.name) == name.lower(),
            Category.deleted_at.is_(None),
            Category.id != (exclude_id or 0),
        )
    )
    if clash is not None:
        raise Conflict("Another category already has this name", code="duplicate_name")


async def _clear_other_fallbacks(db: Db, keep_id: int) -> None:
    for category in await domain.active(db):
        if category.id != keep_id and category.is_fallback:
            category.is_fallback = False


def _rules(body: CategoryIn) -> list[Rule]:
    return [Rule(**rule.model_dump()) for rule in body.rules]


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: Db) -> list[Category]:
    return await domain.active(db)


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryIn, db: Db, settings: Settings, adapters: AdaptersDep, state: State
) -> Category:
    await _check_name(db, body.name)
    await _validate_folder(body.root_folder_path, settings, adapters)
    position = (
        await db.scalar(select(func.max(Category.position)).where(Category.deleted_at.is_(None)))
    ) or 0
    category = Category(
        key=await domain.unique_key(db, body.name),
        name=body.name,
        description=body.description,
        root_folder_path=body.root_folder_path,
        is_fallback=body.is_fallback,
        position=position + 1,
        version=1,
        rules=_rules(body),
    )
    db.add(category)
    await db.flush()
    if body.is_fallback:
        await _clear_other_fallbacks(db, category.id)
    if await domain.reclassify_config_holds(db):
        state.worker.wake()
    await db.commit()
    await db.refresh(category)
    return category


async def _get(db: Db, category_id: int) -> Category:
    category = await db.get(Category, category_id)
    if category is None or category.deleted_at is not None:
        raise NotFound("Unknown category")
    return category


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int, body: CategoryIn, db: Db, settings: Settings, adapters: AdaptersDep, state: State
) -> Category:
    category = await _get(db, category_id)
    await _check_name(db, body.name, exclude_id=category.id)
    if not same_folder(body.root_folder_path, category.root_folder_path):
        await _validate_folder(body.root_folder_path, settings, adapters)
    category.name = body.name
    category.description = body.description
    category.root_folder_path = body.root_folder_path
    category.is_fallback = body.is_fallback
    category.rules = _rules(body)
    category.version += 1
    if body.is_fallback:
        await _clear_other_fallbacks(db, category.id)
    if await domain.reclassify_config_holds(db):
        state.worker.wake()
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, db: Db, state: State) -> None:
    category = await _get(db, category_id)
    if len(await domain.active(db)) <= 1:
        raise Conflict("Keep at least one category", code="last_category")
    category.deleted_at = clock.now()  # past decisions keep referring to it (FR-010)
    category.is_fallback = False
    if await domain.reclassify_config_holds(db):
        state.worker.wake()
    await db.commit()


@router.post("/categories/reorder", status_code=204)
async def reorder(body: ReorderBody, db: Db) -> None:
    by_id = {c.id: c for c in await domain.active(db)}
    for position, category_id in enumerate(body.ids, start=1):
        if category_id in by_id:
            by_id[category_id].position = position
    await db.commit()


async def _locale(db: Db) -> str:
    owner = await db.get(OwnerRow, 1)
    return owner.locale if owner else "en"


@router.get("/presets", response_model=list[PresetOut])
async def list_presets(db: Db) -> list[PresetOut]:
    locale = await _locale(db)
    return [
        PresetOut(
            key=p.key,
            name=p.names[locale],
            description=p.descriptions[locale],
            categories=[
                PresetCategoryOut(
                    name=c.names[locale],
                    description=c.descriptions[locale],
                    is_fallback=c.is_fallback,
                    rule_count=len(c.rules),
                )
                for c in p.categories
            ],
        )
        for p in PRESETS.values()
    ]


@router.post("/presets/{key}/apply", response_model=list[CategoryOut], status_code=201)
async def apply_preset(key: str, db: Db, state: State) -> list[Category]:
    preset = PRESETS.get(key)
    if preset is None:
        raise NotFound("Unknown preset")
    locale = await _locale(db)
    existing = {c.name.lower() for c in await domain.active(db)}
    position = (
        await db.scalar(select(func.max(Category.position)).where(Category.deleted_at.is_(None)))
    ) or 0
    created: list[Category] = []
    for spec in preset.categories:
        name = spec.names[locale]
        candidate, n = name, 2
        while candidate.lower() in existing:
            candidate, n = f"{name} {n}", n + 1
        existing.add(candidate.lower())
        position += 1
        category = Category(
            key=await domain.unique_key(db, candidate),
            name=candidate,
            description=spec.descriptions[locale],
            root_folder_path=None,
            is_fallback=spec.is_fallback,
            position=position,
            version=1,
            rules=[
                Rule(
                    field=r.field,
                    operator=r.operator,
                    value=r.value,
                    weight=r.weight,
                    decisive=r.decisive,
                    excludes=r.excludes,
                )
                for r in spec.rules
            ],
        )
        db.add(category)
        await db.flush()
        if spec.is_fallback:
            await _clear_other_fallbacks(db, category.id)
        created.append(category)
    if await domain.reclassify_config_holds(db):
        state.worker.wake()
    await db.commit()
    for category in created:
        await db.refresh(category)
    return created
