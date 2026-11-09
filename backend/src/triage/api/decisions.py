"""Dashboard, decision history, and decision detail (contracts/http-api.md — Decisions)."""

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, not_, or_, select

from triage.adapters.types import ServiceError
from triage.api.deps import AdaptersDep, Db, Owner, Settings
from triage.core import clock
from triage.core.errors import NotFound
from triage.domain import decisions as d
from triage.domain.categories import active
from triage.domain.classify import tmdb_details
from triage.models import AuditEvent, Category, Decision, MetadataCache, MovieRef

router = APIRouter(tags=["decisions"], dependencies=[Owner])


class MovieOut(BaseModel):
    radarr_id: int
    tmdb_id: int | None
    title: str
    year: int | None
    poster_url: str | None
    root_folder_path: str | None
    added_at: datetime | None = None  # when Radarr added it
    requested_by: str | None = None  # who asked for it in Seerr, when known
    requested_at: datetime | None = None


class CategoryRef(BaseModel):
    id: int
    key: str
    name: str
    root_folder_path: str | None


class DecisionSummary(BaseModel):
    id: int
    status: str
    source: str
    actor: str
    confidence: float
    movie: MovieOut
    top_category: CategoryRef | None
    target_category: CategoryRef | None
    target_root_folder: str | None
    from_root_folder: str | None
    reasons: list[dict[str, Any]]
    error: str | None
    scan_id: int | None
    request_check: dict[str, Any] | None
    created_at: datetime
    decided_at: datetime | None
    # points per category key, the categories ruled out by an exclusion, and the AI's answer:
    # enough to show every choice with its confidence
    scores: dict[str, float]
    excluded: list[str]
    ai: dict[str, Any] | None


class AuditOut(BaseModel):
    at: datetime
    actor: str
    action: str
    from_path: str | None
    to_path: str | None
    result: str
    detail: str | None


class DecisionDetail(DecisionSummary):
    signals: list[dict[str, Any]]
    facts: dict[str, list[str]]
    overview: str | None = None
    threshold: float | None
    margin: int | None
    categories: list[dict[str, Any]]
    audit: list[AuditOut]


class MovieMedia(BaseModel):
    images: list[str] = []  # TMDB file paths, to put behind https://image.tmdb.org/t/p/<size>


class DecisionPage(BaseModel):
    items: list[DecisionSummary]
    next_cursor: int | None


class Counts(BaseModel):
    moved: int
    held: int
    proposed: int
    failed: int
    moving: int
    moved_last_7_days: int


class DayOut(BaseModel):
    day: date
    moved: int  # movies sorted into a library that day
    auto: int  # of which by Triage itself (the rest: by the owner)


class LibraryOut(BaseModel):
    id: int
    key: str
    name: str
    count: int  # movies sorted into it, ever


class Dashboard(BaseModel):
    mode: str
    counts: Counts
    previous_week: int  # sorted the 7 days before the last 7: the trend
    confident: int  # proposals sure enough to apply in one go
    days: list[DayOut]  # the last 30 days, oldest first
    libraries: list[LibraryOut]  # the libraries, the fullest first
    latest: list[DecisionSummary]
    radarr_configured: bool
    ai_enabled: bool
    email_enabled: bool
    categories: int


class ReviewCount(BaseModel):
    review: int


def _category(snapshot: list[dict[str, Any]], category_id: int | None) -> CategoryRef | None:
    if category_id is None:
        return None
    for category in snapshot:
        if category.get("id") == category_id:
            return CategoryRef(
                id=category["id"],
                key=category["key"],
                name=category["name"],
                root_folder_path=category.get("root_folder_path"),
            )
    return None


def _movie(ref: MovieRef | None, radarr_id: int) -> MovieOut:
    if ref is None:
        return MovieOut(
            radarr_id=radarr_id, tmdb_id=None, title="?", year=None, poster_url=None, root_folder_path=None
        )
    return MovieOut(
        radarr_id=ref.radarr_id,
        tmdb_id=ref.tmdb_id,
        title=ref.local_title or ref.title,
        year=ref.year,
        poster_url=ref.poster_url,
        root_folder_path=ref.root_folder_path,
        added_at=ref.added_at,
        requested_by=ref.requested_by,
        requested_at=ref.requested_at,
    )


def summary(decision: Decision, ref: MovieRef | None) -> DecisionSummary:
    snapshot = decision.categories_snapshot or []
    return DecisionSummary(
        id=decision.id,
        status=decision.status,
        source=decision.source,
        actor=decision.actor,
        confidence=decision.confidence,
        movie=_movie(ref, decision.radarr_id),
        top_category=_category(snapshot, decision.top_category_id),
        target_category=_category(snapshot, decision.target_category_id),
        target_root_folder=decision.target_root_folder,
        from_root_folder=decision.from_root_folder,
        reasons=decision.reasons or [],
        error=decision.error,
        scan_id=decision.scan_id,
        request_check=decision.request_check,
        created_at=decision.created_at,
        decided_at=decision.decided_at,
        scores=(decision.scores or {}).get("categories", {}),
        excluded=sorted(
            {str(s["category_key"]) for s in decision.signals or [] if s.get("kind") == "exclusion"}
        ),
        ai=decision.ai,
    )


async def summaries(db: Db, decisions: list[Decision]) -> list[DecisionSummary]:
    ids = {decision.radarr_id for decision in decisions}
    refs = {r.radarr_id: r for r in await db.scalars(select(MovieRef).where(MovieRef.radarr_id.in_(ids)))}
    return [summary(decision, refs.get(decision.radarr_id)) for decision in decisions]


async def _cached_overview(db: Db, ref: MovieRef | None) -> str | None:
    """Decisions made before the overview was kept: the TMDB cache may still have it."""
    if ref is None or not ref.tmdb_id:
        return None
    cached = await db.get(MetadataCache, ref.tmdb_id)
    overview = cached.payload.get("overview") if cached is not None else None
    return str(overview) if overview else None


async def detail(db: Db, decision: Decision) -> DecisionDetail:
    ref = await db.get(MovieRef, decision.radarr_id)
    scores = decision.scores or {}
    events = await db.scalars(
        select(AuditEvent).where(AuditEvent.decision_id == decision.id).order_by(AuditEvent.at, AuditEvent.id)
    )
    return DecisionDetail(
        **summary(decision, ref).model_dump(),
        signals=decision.signals or [],
        facts=scores.get("facts", {}),
        overview=scores.get("overview") or await _cached_overview(db, ref),
        threshold=scores.get("threshold"),
        margin=scores.get("margin"),
        categories=[
            {
                "id": c["id"],
                "key": c["key"],
                "name": c["name"],
                "version": c.get("version", 1),
                "root_folder_path": c.get("root_folder_path"),
                "is_fallback": c.get("is_fallback", False),
            }
            for c in decision.categories_snapshot or []
        ],
        audit=[
            AuditOut(
                at=e.at,
                actor=e.actor,
                action=e.action,
                from_path=e.from_path,
                to_path=e.to_path,
                result=e.result,
                detail=e.detail,
            )
            for e in events
        ],
    )


VISIBLE = Decision.status != d.SIMULATED
# A move back to where the movie came from (an undo, "back to the intake folder"): no category.
PUT_BACK = and_(Decision.source == "correction", Decision.target_category_id.is_(None))
SORTED = and_(Decision.status == d.MOVED, not_(PUT_BACK))


@router.get("/dashboard", response_model=Dashboard)
async def dashboard(db: Db, settings: Settings) -> Dashboard:
    rows = await db.execute(select(Decision.status, func.count()).where(VISIBLE).group_by(Decision.status))
    by_status = {status: int(n) for status, n in rows.all()}
    sorted_ = await db.scalar(select(func.count()).where(SORTED))
    week = await db.scalar(
        select(func.count()).where(SORTED, Decision.decided_at >= clock.now() - timedelta(days=7))
    )
    now = clock.now()
    previous = await db.scalar(
        select(func.count()).where(
            SORTED,
            Decision.decided_at >= now - timedelta(days=14),
            Decision.decided_at < now - timedelta(days=7),
        )
    )
    confident = await db.scalar(
        select(func.count()).where(Decision.status == d.PROPOSED, Decision.confidence > 0)
    )
    # the last 30 days, day by day: what was sorted, and how much of it Triage did alone
    today = now.date()
    per_day = {day: [0, 0] for day in (today - timedelta(days=n) for n in range(29, -1, -1))}
    for decided_at, actor in (
        await db.execute(
            select(Decision.decided_at, Decision.actor).where(
                SORTED,
                Decision.decided_at
                >= datetime.combine(today - timedelta(days=29), datetime.min.time(), tzinfo=now.tzinfo),
            )
        )
    ).all():
        bucket = per_day.get(decided_at.date()) if decided_at else None
        if bucket is not None:
            bucket[0] += 1
            bucket[1] += int(actor == "triage")
    library = func.coalesce(Decision.target_category_id, Decision.top_category_id)
    filled = dict(
        (await db.execute(select(library, func.count()).where(SORTED).group_by(library))).tuples().all()
    )
    libraries = sorted(
        (
            LibraryOut(id=c.id, key=c.key, name=c.name, count=int(filled.get(c.id, 0)))
            for c in await db.scalars(select(Category).where(Category.root_folder_path.is_not(None)))
        ),
        key=lambda lib: (-lib.count, lib.name),
    )
    latest = list(
        await db.scalars(
            select(Decision)
            .where(VISIBLE, Decision.status != d.SUPERSEDED)
            .order_by(Decision.id.desc())
            .limit(10)
        )
    )
    return Dashboard(
        mode=settings.sorting.mode,
        previous_week=int(previous or 0),
        confident=int(confident or 0),
        days=[DayOut(day=day, moved=moved, auto=auto) for day, (moved, auto) in per_day.items()],
        libraries=libraries,
        counts=Counts(
            moved=int(sorted_ or 0),
            held=by_status.get(d.HELD, 0),
            proposed=by_status.get(d.PROPOSED, 0),
            failed=by_status.get(d.FAILED, 0),
            moving=by_status.get(d.MOVING, 0),
            moved_last_7_days=int(week or 0),
        ),
        latest=await summaries(db, latest),
        radarr_configured=settings.radarr_configured and bool(settings.radarr.intake_root_folders),
        ai_enabled=settings.ai_enabled,
        email_enabled=settings.email_enabled,
        categories=len(await active(db)),
    )


@router.get("/decisions", response_model=DecisionPage)
async def list_decisions(
    db: Db,
    status: list[str] = Query(default_factory=list),
    source: str | None = None,
    category: int | None = None,
    q: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: int | None = None,
    limit: int = Query(30, ge=1, le=100),
) -> DecisionPage:
    query = select(Decision).where(VISIBLE)
    if status:
        query = query.where(Decision.status.in_(status))
        if d.MOVED in status:
            query = query.where(not_(PUT_BACK))  # "sorted" means sorted into a library
    else:
        # Superseded decisions (the movie left the intake folder, or was classified again) are
        # history noise: shown only when asked for.
        query = query.where(Decision.status != d.SUPERSEDED)
    if source:
        query = query.where(Decision.source == source)
    if category is not None:
        query = query.where(
            or_(Decision.top_category_id == category, Decision.target_category_id == category)
        )
    if q:
        pattern = f"%{q.strip()}%"
        matching = select(MovieRef.radarr_id).where(
            MovieRef.title.ilike(pattern) | MovieRef.local_title.ilike(pattern)
        )
        query = query.where(Decision.radarr_id.in_(matching))
    if since:
        query = query.where(Decision.created_at >= since)
    if until:
        query = query.where(Decision.created_at <= until)
    if cursor:
        query = query.where(Decision.id < cursor)
    rows = list(await db.scalars(query.order_by(Decision.id.desc()).limit(limit + 1)))
    page = rows[:limit]
    return DecisionPage(
        items=await summaries(db, page), next_cursor=page[-1].id if len(rows) > limit and page else None
    )


@router.get("/decisions/{decision_id}", response_model=DecisionDetail)
async def get_decision(decision_id: int, db: Db) -> DecisionDetail:
    decision = await db.get(Decision, decision_id)
    if decision is None:
        raise NotFound("Unknown decision")
    return await detail(db, decision)


@router.get("/movies/{radarr_id}/media", response_model=MovieMedia)
async def movie_media(radarr_id: int, db: Db, settings: Settings, adapters: AdaptersDep) -> MovieMedia:
    """A few TMDB stills, to see at a glance whether Radarr matched the right movie. Best effort:
    without TMDB there are none."""
    ref = await db.get(MovieRef, radarr_id)
    try:
        details = await tmdb_details(db, adapters, ref.tmdb_id if ref else None, settings.tmdb.language)
        await db.commit()
    except ServiceError:
        details = None
    return MovieMedia(images=list(details.images) if details else [])


@router.get("/review/count", response_model=ReviewCount)
async def review_count(db: Db) -> ReviewCount:
    count = await db.scalar(select(func.count()).where(Decision.status.in_([d.HELD, d.PROPOSED])))
    return ReviewCount(review=int(count or 0))
