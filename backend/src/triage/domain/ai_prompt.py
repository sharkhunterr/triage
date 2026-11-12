"""What the local AI is told: the owner's categories in their own words with their folders and
rules, then the movie's facts and the categories its rules rule out. Not the points the rules gave:
the AI is a second opinion on what the movie is, and a tally to agree with only anchors it.

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
Metadata tags are often missing or misleading: a keyword alone does not make a category (a drama
about a singer is tagged "concert", it is not a concert film). Judge what the movie actually is from
its title, overview and your own knowledge of it, and use the rules as hints.
First write one or two sentences of reasoning, written in {language}: what the movie actually is.
Then choose the category that reasoning leads to, and give a confidence between 0 and 1.
If you cannot decide with reasonable certainty, answer "unsure".

Categories:
{categories}"""

LABELS = {
    "genre": "Genres",
    "keyword": "Keywords",
    "company": "Production companies",
    "certification": "Age ratings",
    "original_language": "Original language",
    "wikidata": "Kind of work (Wikidata)",
}
# the reasoning is shown to the owner: it follows the TMDB language ("fr-FR" → French)
LANGUAGES = {
    "fr": "French",
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
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


def _ruled_out(result: ScoreResult, categories: list[CategoryDef]) -> list[str]:
    lines: list[str] = []
    for category in categories:
        excluded = [
            s for s in result.signals if s["kind"] == "exclusion" and s["category_key"] == category.key
        ]
        if excluded:
            why = "; ".join(f"{s['field']} is {s['value']}" for s in excluded)
            lines.append(f"- {category.key} ({why})")
    return ["Ruled out by the owner's rules (never choose them):", *lines] if lines else []


def build_prompt(
    facts: MovieFacts,
    categories: list[CategoryDef],
    result: ScoreResult | None = None,
    language: str = "en-US",
) -> tuple[str, str]:
    system = SYSTEM.format(
        categories="\n".join(_category(c) for c in categories),
        language=LANGUAGES.get(language.split("-")[0], "English"),
    )

    summary = facts.summary()
    user_lines = [f"Title: {facts.title}" + (f" ({facts.year})" if facts.year else "")]
    for field, label in LABELS.items():
        if summary[field]:
            user_lines.append(f"{label}: {', '.join(summary[field][:30])}")
    if facts.overview:
        user_lines.append(f"Overview: {facts.overview[:1500]}")
    if facts.wikipedia:
        user_lines.append(f"Wikipedia: {facts.wikipedia}")
    ruled_out = _ruled_out(result, categories) if result is not None else []
    if ruled_out:
        user_lines += ["", *ruled_out]
    return system, "\n".join(user_lines)
