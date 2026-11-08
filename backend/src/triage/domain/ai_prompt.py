"""What the local AI is told: the owner's categories in their own words, then the movie's facts.

The answer is constrained by a JSON schema (adapters.ollama); the prompt only explains the task.
"""

from triage.domain.scoring import CategoryDef
from triage.domain.signals import MovieFacts

SYSTEM = """You sort movies into a home media library.
Choose the one category whose description fits the movie best, using the movie's facts.
If the facts do not let you decide with reasonable certainty, answer "unsure".
Give a confidence between 0 and 1 and one or two sentences of reasoning.

Categories (key: description):
{categories}"""


def build_prompt(facts: MovieFacts, categories: list[CategoryDef]) -> tuple[str, str]:
    lines = []
    for category in categories:
        description = category.description.strip() or category.name
        suffix = " (used when nothing else fits)" if category.is_fallback else ""
        lines.append(f"- {category.key}: {category.name} — {description}{suffix}")
    system = SYSTEM.format(categories="\n".join(lines))

    summary = facts.summary()
    user_lines = [f"Title: {facts.title}" + (f" ({facts.year})" if facts.year else "")]
    labels = {
        "genre": "Genres",
        "keyword": "Keywords",
        "company": "Production companies",
        "certification": "Age ratings",
        "original_language": "Original language",
    }
    for field, label in labels.items():
        if summary[field]:
            user_lines.append(f"{label}: {', '.join(summary[field][:30])}")
    if facts.overview:
        user_lines.append(f"Overview: {facts.overview[:1500]}")
    return system, "\n".join(user_lines)
