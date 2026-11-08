"""Metadata facts about a movie, gathered from Radarr and (when configured) TMDB.

These are *facts*: values the services report. The AI's view is kept apart (Constitution III).
"""

import unicodedata
from dataclasses import dataclass, field

from triage.adapters.types import RadarrMovie, TmdbDetails

FIELDS = ("genre", "keyword", "company", "certification", "original_language")


def normalize(value: str) -> str:
    """Case- and accent-insensitive form used to compare rule values and facts."""
    decomposed = unicodedata.normalize("NFKD", value.casefold().strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@dataclass(frozen=True)
class Fact:
    field: str
    value: str
    source: str  # radarr | tmdb


@dataclass
class MovieFacts:
    title: str
    year: int | None
    overview: str | None
    facts: list[Fact] = field(default_factory=list)

    def values(self, field_name: str) -> list[Fact]:
        return [f for f in self.facts if f.field == field_name]

    @property
    def has_metadata(self) -> bool:
        return any(f.field in ("genre", "keyword", "company") for f in self.facts)

    def summary(self) -> dict[str, list[str]]:
        return {name: sorted({f.value for f in self.values(name)}) for name in FIELDS}


def gather_facts(movie: RadarrMovie, details: TmdbDetails | None) -> MovieFacts:
    facts: list[Fact] = []
    seen: set[tuple[str, str]] = set()

    def add(field_name: str, value: str | None, source: str) -> None:
        if not value or not value.strip():
            return
        key = (field_name, normalize(value))
        if key not in seen:
            seen.add(key)
            facts.append(Fact(field_name, value.strip(), source))

    for genre in movie.genres:
        add("genre", genre, "radarr")
    for keyword in movie.keywords:
        add("keyword", keyword, "radarr")
    add("company", movie.studio, "radarr")
    add("certification", movie.certification, "radarr")
    add("original_language", movie.original_language, "radarr")
    overview = movie.overview
    if details is not None:
        for genre in details.genres:
            add("genre", genre, "tmdb")
        for keyword in details.keywords:
            add("keyword", keyword, "tmdb")
        for company in details.companies:
            add("company", company, "tmdb")
        for certification in details.certifications:
            add("certification", certification, "tmdb")
        add("original_language", details.original_language, "tmdb")
        overview = details.overview or overview  # TMDB's is in the configured language
    return MovieFacts(title=movie.title, year=movie.year, overview=overview, facts=facts)
