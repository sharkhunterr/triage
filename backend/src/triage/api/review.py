"""The review queue, the owner's choice on a decision, and the one-click email links."""

from typing import Annotated

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, model_validator
from sqlalchemy import select

from triage.api.decisions import DecisionDetail, DecisionSummary, detail, summaries
from triage.api.deps import Db, Owner, Settings, State
from triage.core.errors import Gone, NotFound
from triage.core.tokens import usable_link, use
from triage.domain import actions
from triage.domain import decisions as d
from triage.models import Decision, MovieRef
from triage.models import Owner as OwnerRow
from triage.templates.messages import text
from triage.templates.render import app_link, confirm_form, page

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
