"""What the local AI is told: the owner's categories in their own words with their folders and
rules, then the movie's facts and what the rules already found.

The answer is constrained by a JSON schema (adapters.ollama); the prompt only explains the task.
"""

from triage.domain.scoring import CategoryDef, RuleDef, ScoreResult
from triage.domain.signals import MovieFacts

SYSTEM = """You sort movies into a home media library. Each category is a folder of the library.
Choose the one category that fits the movie best, using the movie's facts, the category
descriptions and the owner's rules.

The rules are the owner's own criteria:
- "Signals" point toward a category; the number is how much they count, and a "decisive" one settles it.
- "Never when" rules are exclusions: never choose a category ruled out by one of them.
- The fallback category is used when nothing else fits.
Use the rules as guidance and your knowledge of the movie (overview, style, audience) for the rest.
If you cannot decide with reasonable certainty, answer "unsure".
Give a confidence between 0 and 1 and one or two sentences of reasoning.

Categories:
{categories}"""

LABELS = {
    "genre": "Genres",
    "keyword": "Keywords",
    "company": "Production companies",
    "certification": "Age ratings",
    "original_language": "Original language",
}
OPERATORS = {"is": "is", "contains": "contains", "is_not": "is not"}


def _rule(rule: RuleDef) -> str:
    return f"{rule.field} {OPERATORS.get(rule.operator, rule.operator)} {rule.value}"


def _category(category: CategoryDef) -> str:
    description = category.description.strip() or category.name
    head = f"- {category.key}: {category.name}"
    if category.root_folder_path:
        head += f" (folder {category.root_folder_path})"
    if category.is_fallback:
        head += " (fallback: used when nothing else fits)"
    lines = [head, f"  Description: {description}"]
    signals = [
        f"{_rule(r)} (+{r.weight}{', decisive' if r.decisive else ''})"
        for r in category.rules
        if not r.excludes
    ]
    exclusions = [_rule(r) for r in category.rules if r.excludes]
    if signals:
        lines.append(f"  Signals: {'; '.join(signals)}")
    if exclusions:
        lines.append(f"  Never when: {'; '.join(exclusions)}")
    return "\n".join(lines)


def _findings(result: ScoreResult, categories: list[CategoryDef]) -> list[str]:
    lines = ["What the rules found:"]
    for category in categories:
        excluded = [
            s for s in result.signals if s["kind"] == "exclusion" and s["category_key"] == category.key
        ]
        if excluded:
            why = "; ".join(f"{s['field']} is {s['value']}" for s in excluded)
            lines.append(f"- {category.key}: ruled out ({why})")
            continue
        matched = [
            f"{s['field']} {s['value']}"
            for s in result.signals
            if s["kind"] == "fact" and s["category_key"] == category.key
        ]
        if any(s["kind"] == "fallback" and s["category_key"] == category.key for s in result.signals):
            matched.append("fallback")
        points = round(result.scores.get(category.key, 0))
        lines.append(f"- {category.key}: {points} points" + (f" ({', '.join(matched)})" if matched else ""))
    return lines


def build_prompt(
    facts: MovieFacts, categories: list[CategoryDef], result: ScoreResult | None = None
) -> tuple[str, str]:
    system = SYSTEM.format(categories="\n".join(_category(c) for c in categories))

    summary = facts.summary()
    user_lines = [f"Title: {facts.title}" + (f" ({facts.year})" if facts.year else "")]
    for field, label in LABELS.items():
        if summary[field]:
            user_lines.append(f"{label}: {', '.join(summary[field][:30])}")
    if facts.overview:
        user_lines.append(f"Overview: {facts.overview[:1500]}")
    if result is not None:
        user_lines += ["", *_findings(result, categories)]
    return system, "\n".join(user_lines)
