"""The review queue, the owner's choice on a decision, and the one-click email links."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from triage.api.decisions import DecisionDetail, DecisionSummary, detail, summaries
from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core.errors import Conflict, Gone, NotFound
from triage.core.tokens import usable_link, use
from triage.domain import actions, categories
from triage.domain import decisions as d
from triage.domain.arrivals import upsert_movie
from triage.domain.classify import classify_movie
from triage.models import Decision, MovieRef
from triage.models import Owner as OwnerRow
from triage.templates.messages import text
from triage.templates.render import app_link, confirm_form, page
from triage.worker import queue
from triage.worker.classify import new_decision

router = APIRouter(tags=["review"], dependencies=[Owner])
public = APIRouter(tags=["review links"])


class ChoiceBody(BaseModel):
    category_id: int | None = None
    target: str | None = None

    @model_validator(mode="after")
    def _one(self) -> "ChoiceBody":
        if (self.category_id is None) == (self.target is None) or self.target not in (None, actions.INTAKE):
            raise ValueError("Give either category_id or target='intake'")
        return self

    @property
    def choice(self) -> int | str:
        return self.category_id if self.category_id is not None else actions.INTAKE


@router.get("/review", response_model=list[DecisionSummary])
async def review_queue(db: Db) -> list[DecisionSummary]:
    rows = await db.scalars(
        select(Decision)
        .where(Decision.status.in_([d.HELD, d.PROPOSED]))
        .order_by(Decision.created_at, Decision.id)
    )
    return await summaries(db, list(rows))


async def _decision(db: Db, decision_id: int) -> Decision:
    decision = await db.get(Decision, decision_id)
    if decision is None:
        raise NotFound("Unknown decision")
    return decision


@router.post("/decisions/{decision_id}/apply", response_model=DecisionDetail)
async def apply(decision_id: int, body: ChoiceBody, db: Db, state: State) -> DecisionDetail:
    decision = await _decision(db, decision_id)
    await actions.choose(db, decision, body.choice)
    await db.commit()
    state.worker.wake()
    return await detail(db, decision)


# ---------------------------------------------------------------------- email links (public)
async def _locale(db: Db) -> str:
    owner = await db.get(OwnerRow, 1)
    return owner.locale if owner else "en"


def _gone(locale: str, base_url: str) -> HTMLResponse:
    body = page(
        locale,
        text(locale, "page.goneTitle"),
        text(locale, "page.goneText"),
        link=app_link(base_url, text(locale, "page.openApp")),
    )
    return HTMLResponse(body, status_code=410)


async def _choice_label(db: Db, locale: str, choice: str) -> tuple[int | str, str] | None:
    if choice == actions.INTAKE:
        return actions.INTAKE, ""
    category = await actions.category_by_key(db, choice)
    if category is None or not category.root_folder_path:
        return None
    return category.id, category.name


@public.get("/r/{token}", response_class=HTMLResponse, include_in_schema=False)
async def link_page(token: str, db: Db, settings: Settings, c: Annotated[str, Query()] = "") -> HTMLResponse:
    """Opening a link only shows a confirmation: mail scanners that open links act on nothing."""
    locale = await _locale(db)
    try:
        link = await usable_link(db, token)
    except Gone:
        return _gone(locale, settings.base_url)
    decision = await db.get(Decision, link.decision_id)
    ref = await db.get(MovieRef, decision.radarr_id) if decision else None
    resolved = await _choice_label(db, locale, c)
    if decision is None or resolved is None:
        return HTMLResponse(
            page(locale, text(locale, "page.badTitle"), text(locale, "page.badText")), status_code=400
        )
    title = ref.title if ref else "?"
    _, name = resolved
    message = (
        text(locale, "page.confirmLeave")
        if c == actions.INTAKE
        else text(locale, "page.confirmMove", category=name)
    )
    return HTMLResponse(
        page(
            locale,
            text(locale, "page.confirmTitle", title=title),
            message,
            form=confirm_form(c, text(locale, "page.confirm")),
        )
    )


@public.post("/r/{token}", response_class=HTMLResponse, include_in_schema=False)
async def link_confirm(
    token: str, db: Db, settings: Settings, state: State, c: Annotated[str, Form()] = ""
) -> HTMLResponse:
    locale = await _locale(db)
    try:
        link = await usable_link(db, token)
    except Gone:
        return _gone(locale, settings.base_url)
    decision = await db.get(Decision, link.decision_id)
    resolved = await _choice_label(db, locale, c)
    if decision is None or resolved is None:
        return HTMLResponse(
            page(locale, text(locale, "page.badTitle"), text(locale, "page.badText")), status_code=400
        )
    choice, name = resolved
    if decision.status not in {d.HELD, d.PROPOSED}:
        return _gone(locale, settings.base_url)
    use(link, c)
    await actions.choose(db, decision, choice)
    await db.commit()
    state.worker.wake()
    ref = await db.get(MovieRef, decision.radarr_id)
    title = ref.title if ref else "?"
    message = (
        text(locale, "page.doneLeave", title=title)
        if choice == actions.INTAKE
        else text(locale, "page.doneMove", title=title, category=name)
    )
    return HTMLResponse(
        page(
            locale,
            text(locale, "page.doneTitle"),
            message,
            link=app_link(settings.base_url, text(locale, "page.openApp")),
        )
    )


# ---------------------------------------------------------------------- preview (US4)
@router.post("/decisions/{decision_id}/dismiss", response_model=DecisionDetail)
async def dismiss(decision_id: int, db: Db) -> DecisionDetail:
    decision = await _decision(db, decision_id)
    if decision.status != d.PROPOSED:
        raise Conflict("Only a proposal can be dismissed", code="not_a_proposal")
    await actions.choose(db, decision, actions.INTAKE)
    await db.commit()
    return await detail(db, decision)


class ApplyConfidentBody(BaseModel):
    scan_id: int | None = None


class Applied(BaseModel):
    applied: int


@router.post("/decisions/apply-confident", response_model=Applied)
async def apply_confident(body: ApplyConfidentBody, db: Db, settings: Settings, state: State) -> Applied:
    """Apply every proposal at or above the threshold (optionally of one scan)."""
    query = select(Decision).where(
        Decision.status == d.PROPOSED, Decision.confidence >= settings.sorting.threshold
    )
    if body.scan_id is not None:
        query = query.where(Decision.scan_id == body.scan_id)
    applied = 0
    for decision in await db.scalars(query.order_by(Decision.id)):
        if decision.target_category_id is None:
            continue
        try:
            await actions.choose(db, decision, decision.target_category_id)
        except NotFound:
            continue  # its category lost its library since: leave the proposal
        applied += 1
    await db.commit()
    if applied:
        state.worker.wake()
    return Applied(applied=applied)


@router.post("/movies/{radarr_id}/simulate", response_model=DecisionDetail)
async def simulate(radarr_id: int, db: Db, settings: Settings, adapters: AdaptersDep) -> DecisionDetail:
    """What Triage would decide for this movie now. Recorded for display only: never moves,
    never emails, never appears in history or review."""
    if adapters.radarr is None:
        raise NotFound("Radarr is not connected", code="radarr_not_configured")
    movie = await adapters.radarr.movie(radarr_id)
    if movie is None:
        raise NotFound("Radarr has no such movie")
    await upsert_movie(db, movie)
    result = await classify_movie(db, settings, adapters, movie)
    decision = new_decision(movie.id, "simulation", result, movie.root_folder_path)
    decision.status = d.SIMULATED
    db.add(decision)
    await db.commit()
    return await detail(db, decision)


@router.post("/decisions/{decision_id}/correct", response_model=DecisionDetail)
async def correct(
    decision_id: int, body: ChoiceBody, db: Db, settings: Settings, state: State
) -> DecisionDetail:
    decision = await _decision(db, decision_id)
    correction = await actions.correct(db, decision, body.choice, settings.radarr.intake_root_folders)
    await db.commit()
    state.worker.wake()
    return await detail(db, correction)


@router.post("/decisions/{decision_id}/revert", response_model=DecisionDetail)
async def revert(decision_id: int, db: Db, state: State) -> DecisionDetail:
    """Undo a move: back to the folder the movie came from."""
    decision = await _decision(db, decision_id)
    correction = await actions.revert(db, decision)
    await db.commit()
    state.worker.wake()
    return await detail(db, correction)


class RevertBody(BaseModel):
    since: datetime | None = None
    dry_run: bool = False


class Reverted(BaseModel):
    count: int
    items: list[DecisionSummary]


@router.post("/decisions/revert", response_model=Reverted)
async def revert_many(body: RevertBody, db: Db, state: State) -> Reverted:
    """Undo every move made since ``since`` (all of them without it). ``dry_run`` only lists them."""
    since = body.since
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=UTC)  # a time without a zone is taken as UTC
    moves = await actions.revertable(db, since)
    listed = await summaries(db, moves)
    if not body.dry_run and moves:
        for decision in moves:
            await actions.revert(db, decision)
        await db.commit()
        state.worker.wake()
    return Reverted(count=len(moves), items=listed)


class ReanalyzeBody(BaseModel):
    dry_run: bool = False


class Count(BaseModel):
    count: int


@router.post("/decisions/reanalyze", response_model=Count)
async def reanalyze(body: ReanalyzeBody, db: Db, state: State) -> Count:
    """Every movie waiting in the intake folder, classified again with today's rules."""
    count = await categories.reanalyze_waiting(db, dry_run=body.dry_run)
    if not body.dry_run:
        await queue.enqueue(db, "refresh_titles", {})
        await db.commit()
        if count:
            state.worker.wake()
    return Count(count=count)


class BulkItem(ChoiceBody):
    id: int


class BulkBody(BaseModel):
    items: list[BulkItem] = Field(max_length=500)


class BulkResult(BaseModel):
    applied: int
    failed: list[int]


@router.post("/decisions/bulk", response_model=BulkResult)
async def decide_many(body: BulkBody, db: Db, state: State) -> BulkResult:
    """Several choices at once (the review dialog). One that cannot be applied is reported."""
    applied, failed = 0, []
    for item in body.items:
        decision = await db.get(Decision, item.id)
        try:
            if decision is None:
                raise NotFound("Unknown decision")
            await actions.choose(db, decision, item.choice)
        except (Conflict, NotFound):
            failed.append(item.id)
            continue
        applied += 1
    await db.commit()
    if applied:
        state.worker.wake()
    return BulkResult(applied=applied, failed=failed)
