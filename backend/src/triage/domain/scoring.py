"""The scoring engine (research R5): deterministic rules first, the AI as one more signal.

Every number the interface shows comes from here, so a decision can be explained line by line
(Constitution III, IV). Categories are passed as snapshots, the same ones stored on the
decision, so a past decision can always be re-read with the rules in force at the time.
"""

from dataclasses import dataclass, field
from typing import Any

from triage.adapters.types import AiVerdict
from triage.domain.signals import MovieFacts, normalize

PRIOR = 20.0  # keeps a single weak signal from ever reaching a high confidence
FALLBACK_BASE = 100.0  # the fallback's score when no other category has any signal
UNSURE = "unsure"


@dataclass(frozen=True)
class RuleDef:
    id: int
    field: str
    operator: str
    value: str
    weight: int
    decisive: bool
    # When it matches, its category is ruled out: no score, no decisive win, no AI vote.
    excludes: bool = False


@dataclass(frozen=True)
class CategoryDef:
    id: int
    key: str
    name: str
    description: str
    root_folder_path: str | None
    is_fallback: bool
    version: int
    rules: tuple[RuleDef, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "root_folder_path": self.root_folder_path,
            "is_fallback": self.is_fallback,
            "version": self.version,
            "rules": [r.__dict__ for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CategoryDef":
        return cls(
            id=data["id"],
            key=data["key"],
            name=data["name"],
            description=data.get("description", ""),
            root_folder_path=data.get("root_folder_path"),
            is_fallback=bool(data.get("is_fallback")),
            version=int(data.get("version", 1)),
            rules=tuple(RuleDef(**r) for r in data.get("rules", [])),
        )


@dataclass
class ScoreResult:
    scores: dict[str, float]
    signals: list[dict[str, Any]]
    top: str | None
    second: str | None
    confidence: float
    decisive: str | None
    conclusive: bool
    reasons: list[dict[str, Any]] = field(default_factory=list)

    @property
    def margin(self) -> float:
        if self.top is None:
            return 0.0
        return self.scores[self.top] - (self.scores[self.second] if self.second else 0.0)


def _matches(rule: RuleDef, facts: MovieFacts) -> str | None:
    """The fact value the rule matched (or the rule value for ``is_not``), else None."""
    wanted = normalize(rule.value)
    values = facts.values(rule.field)
    if rule.operator == "is":
        return next((f.value for f in values if normalize(f.value) == wanted), None)
    if rule.operator == "contains":
        return next((f.value for f in values if wanted in normalize(f.value)), None)
    if rule.operator == "is_not":
        return None if any(normalize(f.value) == wanted for f in values) else rule.value
    return None


def score(
    facts: MovieFacts,
    categories: list[CategoryDef],
    *,
    threshold: float,
    margin: int,
    ai: AiVerdict | None = None,
    ai_weight: int = 60,
) -> ScoreResult:
    scores: dict[str, float] = {c.key: 0.0 for c in categories}
    signals: list[dict[str, Any]] = []
    decisive_hits: list[str] = []

    excluded: set[str] = set()
    for category in categories:
        for rule in category.rules:
            if not rule.excludes:
                continue
            value = _matches(rule, facts)
            if value is None:
                continue
            excluded.add(category.key)
            signals.append(
                {
                    "kind": "exclusion",
                    "field": rule.field,
                    "operator": rule.operator,
                    "value": value,
                    "rule_id": rule.id,
                    "category_key": category.key,
                    "weight": 0,
                }
            )

    for category in categories:
        for rule in category.rules:
            if rule.excludes:
                continue
            value = _matches(rule, facts)
            if value is None:
                continue
            ignored = category.key in excluded
            if not ignored:
                scores[category.key] += rule.weight
            signals.append(
                {
                    "kind": "fact",
                    "field": rule.field,
                    "operator": rule.operator,
                    "value": value,
                    "rule_id": rule.id,
                    "category_key": category.key,
                    "weight": rule.weight,
                    "decisive": rule.decisive,
                    "ignored": ignored,
                }
            )
            if rule.decisive and not ignored and category.key not in decisive_hits:
                decisive_hits.append(category.key)

    fallback = next((c for c in categories if c.is_fallback), None)
    # The fallback's base is a default, not evidence: when the AI points elsewhere (and nothing rules
    # its choice out), the movie is not "nothing else fits" any more — the AI's pick competes alone.
    ai_elsewhere = (
        ai is not None
        and fallback is not None
        and ai.category in scores
        and ai.category != fallback.key
        and ai.category not in excluded
        and not decisive_hits
    )
    unmatched = not any(scores[c.key] > 0 for c in categories if not c.is_fallback)
    if fallback is not None and unmatched and not ai_elsewhere:
        scores[fallback.key] += FALLBACK_BASE
        signals.append(
            {"kind": "fallback", "category_key": fallback.key, "weight": FALLBACK_BASE, "value": None}
        )

    if ai is not None and ai.category != UNSURE and ai.category in scores and not decisive_hits:
        contribution = round(ai_weight * ai.confidence, 1)
        ignored = ai.category in excluded
        if not ignored:
            scores[ai.category] += contribution
        signals.append(
            {
                "kind": "inference",
                "category_key": ai.category,
                "weight": contribution,
                "value": ai.reasoning,
                "ignored": ignored,
            }
        )

    ranked = sorted(categories, key=lambda c: (-scores[c.key], c.key))
    top = ranked[0].key if ranked and scores[ranked[0].key] > 0 else None
    second = ranked[1].key if len(ranked) > 1 and scores[ranked[1].key] > 0 else None
    reasons: list[dict[str, Any]] = []

    if len(decisive_hits) > 1:
        reasons.append({"code": "decisive_conflict", "categories": decisive_hits})
        return ScoreResult(scores, signals, top, second, 0.0, None, False, reasons)
    if decisive_hits:
        return ScoreResult(scores, signals, decisive_hits[0], second, 1.0, decisive_hits[0], True, reasons)

    if top is None:
        reasons.append({"code": "no_signal"})
        return ScoreResult(scores, signals, None, None, 0.0, None, False, reasons)

    top_score = scores[top]
    second_score = scores[second] if second else 0.0
    confidence = round(top_score / (top_score + second_score + PRIOR), 3)
    conclusive = True
    if ai_elsewhere and unmatched and top == (ai.category if ai else None):
        reasons.append({"code": "ai_only", "category": top})
    if confidence < threshold:
        conclusive = False
        reasons.append({"code": "low_confidence", "confidence": confidence, "threshold": threshold})
    if top_score - second_score < margin:
        conclusive = False
        reasons.append({"code": "close_second", "top": top, "second": second, "margin": margin})
    return ScoreResult(scores, signals, top, second, confidence, None, conclusive, reasons)
