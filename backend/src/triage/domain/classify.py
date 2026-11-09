"""Classify one Radarr movie: gather facts, score with the rules, ask the AI only if needed.

Shared by intake arrivals, scans, and simulations so they always agree.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from triage.adapters.types import Adapters, AiVerdict, RadarrMovie, ServiceError, TmdbDetails
from triage.core import clock
from triage.core.activity import FAILED, note, skip, step
from triage.core.settings import AppSettings
from triage.domain.ai_prompt import build_prompt
from triage.domain.categories import definitions
from triage.domain.scoring import UNSURE, CategoryDef, score
from triage.domain.signals import gather_facts
from triage.models import MetadataCache, MovieRef

CACHE_TTL = timedelta(days=7)
CACHE_VERSION = 3  # 2: translated titles, the country's own translation first; 3: images


@dataclass
class Classification:
    signals: list[dict[str, Any]]
    scores: dict[str, Any]
    reasons: list[dict[str, Any]]
    confidence: float
    conclusive: bool
    top: CategoryDef | None
    ai: dict[str, Any] | None
    snapshot: list[dict[str, Any]] = field(default_factory=list)

    @property
    def target_folder(self) -> str | None:
        return self.top.root_folder_path if self.top else None


async def tmdb_details(
    db: AsyncSession, adapters: Adapters, tmdb_id: int | None, language: str = "en-US"
) -> TmdbDetails | None:
    """TMDB facts, cached 7 days per language. Raises ServiceError when TMDB is configured but
    failing: the job is retried rather than deciding on partial facts (Constitution VI)."""
    if adapters.tmdb is None or not tmdb_id:
        return None
    cached = await db.get(MetadataCache, tmdb_id)
    fresh = cached is not None and clock.now() - cached.fetched_at < CACHE_TTL
    # an entry written by an older reading of TMDB (another CACHE_VERSION) is read again
    if (
        cached is not None
        and fresh
        and cached.payload.get("language", "en-US") == language
        and cached.payload.get("v") == CACHE_VERSION
    ):
        payload = cached.payload
        return TmdbDetails(
            genres=tuple(payload.get("genres") or ()),
            keywords=tuple(payload.get("keywords") or ()),
            companies=tuple(payload.get("companies") or ()),
            certifications=tuple(payload.get("certifications") or ()),
            original_language=payload.get("original_language"),
            overview=payload.get("overview"),
            title=payload.get("title"),
            images=tuple(payload.get("images") or ()),
        )
    details = await adapters.tmdb.details(tmdb_id)
    payload = {k: list(v) if isinstance(v, tuple) else v for k, v in details.__dict__.items()}
    payload["language"] = language
    payload["v"] = CACHE_VERSION
    if cached is None:
        db.add(MetadataCache(tmdb_id=tmdb_id, payload=payload, fetched_at=clock.now()))
    else:
        cached.payload = payload
        cached.fetched_at = clock.now()
    await db.flush()
    return details


def _verdict(names: dict[str, str], key: str | None, confidence: float) -> str:
    return f"{names.get(key, key)} · {round(confidence * 100)} %" if key else "—"


def _why_not_asked(settings: AppSettings, adapters: Adapters, conclusive: bool) -> str:
    if adapters.ollama is None:
        return "off"
    if settings.ollama.ask == "never":
        return "never"
    return "rules_sure" if conclusive else "conflict"


def _should_ask(mode: str, conclusive: bool) -> bool:
    return mode == "always" or (mode == "when_unsure" and not conclusive)


async def classify_movie(
    db: AsyncSession, settings: AppSettings, adapters: Adapters, movie: RadarrMovie
) -> Classification:
    categories = await definitions(db)
    snapshot = [c.to_dict() for c in categories]
    if not categories:
        return Classification([], {}, [{"code": "no_categories"}], 0.0, False, None, None, snapshot)

    # Never hold SQLite's write lock while waiting on the network (TMDB, the AI): what was written
    # so far (the movie, cached metadata) is safe to keep, and the interface stays writable.
    await db.commit()
    with step("metadata") as metadata:
        details = await tmdb_details(db, adapters, movie.tmdb_id, settings.tmdb.language)
        metadata.detail = "TMDB" if details is not None else "Radarr"
    if details is not None:
        ref = await db.get(MovieRef, movie.id)
        if ref is not None:
            ref.local_title = details.title  # None: Radarr's title is the right one
        if details.title:
            note(title=details.title)
    facts = gather_facts(movie, details)
    sorting = settings.sorting
    names = {c.key: c.name for c in categories}
    with step("rules") as rules:
        result = score(facts, categories, threshold=sorting.threshold, margin=sorting.margin)
        rules.detail = _verdict(names, result.top, result.confidence)
    reasons = list(result.reasons)
    ai: dict[str, Any] | None = None

    if not facts.has_metadata:
        reasons = [{"code": "no_metadata"}]
        result.conclusive = False
        skip("ai", "no_metadata")
    elif (
        adapters.ollama is not None
        and _should_ask(settings.ollama.ask, result.conclusive)
        and not any(r["code"] == "decisive_conflict" for r in reasons)
    ):
        asked = "unsure" if not result.conclusive else "always"
        system, user = build_prompt(facts, categories, result, settings.tmdb.language)
        await db.commit()
        verdict: AiVerdict | None = None
        with step("ai") as asking:
            try:
                verdict = await adapters.ollama.classify(system, user, [c.key for c in categories])
            except ServiceError as exc:
                asking.state, asking.detail = FAILED, exc.message
            else:
                chosen = None if verdict.category == UNSURE else verdict.category
                asking.detail = f"{settings.ollama.model} · " + _verdict(names, chosen, verdict.confidence)
        if verdict is None:
            # A second opinion that fails never blocks what the rules are sure of (Constitution IV).
            ai = {"error": asking.detail, "asked": asked}
            if not result.conclusive:
                reasons.append({"code": "ai_unavailable", "error": asking.detail})
        else:
            ai = {
                "asked": asked,
                "model": settings.ollama.model,
                "category": verdict.category,
                "confidence": verdict.confidence,
                "reasoning": verdict.reasoning,
                "duration_ms": verdict.duration_ms,
            }
            result = score(
                facts,
                categories,
                threshold=sorting.threshold,
                margin=sorting.margin,
                ai=verdict,
                ai_weight=sorting.ai_weight,
            )
            reasons = list(result.reasons)
            if verdict.category == UNSURE and not result.conclusive:
                reasons.append({"code": "ai_unsure"})
    else:
        skip("ai", _why_not_asked(settings, adapters, result.conclusive))

    top = next((c for c in categories if c.key == result.top), None)
    conclusive = result.conclusive
    if conclusive and top is not None and not top.root_folder_path:
        conclusive = False
        reasons.append({"code": "category_without_folder", "category": top.key})

    scores = {
        "categories": result.scores,
        "facts": facts.summary(),
        "threshold": sorting.threshold,
        "margin": sorting.margin,
        "decisive": result.decisive,
        "overview": facts.overview,
    }
    return Classification(result.signals, scores, reasons, result.confidence, conclusive, top, ai, snapshot)
