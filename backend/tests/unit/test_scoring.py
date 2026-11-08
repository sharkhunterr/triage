from triage.adapters.types import AiVerdict, RadarrMovie, TmdbDetails
from triage.domain.scoring import CategoryDef, RuleDef, score
from triage.domain.signals import gather_facts


def rule(rid: int, field: str, value: str, weight: int, *, op: str = "is", decisive: bool = False) -> RuleDef:
    return RuleDef(id=rid, field=field, operator=op, value=value, weight=weight, decisive=decisive)


ANIMATION = CategoryDef(
    id=1,
    key="animation",
    name="Dessins Animés",
    description="Animated films for the family",
    root_folder_path="/media/animation",
    is_fallback=False,
    version=1,
    rules=(
        rule(1, "genre", "Animation", 60),
        rule(2, "keyword", "anime", 30),
        rule(3, "company", "Pixar", 40),
        rule(4, "company", "Studio Ghibli", 40),
    ),
)
FILMS = CategoryDef(
    id=2,
    key="films",
    name="Films",
    description="Everything else",
    root_folder_path="/media/films",
    is_fallback=True,
    version=1,
    rules=(rule(5, "keyword", "live action", 40, op="contains"),),
)


def facts(genres=(), keywords=(), companies=(), language=None):
    movie = RadarrMovie(
        id=1, tmdb_id=1, title="T", year=2000, root_folder_path="/intake", genres=tuple(genres)
    )
    return gather_facts(
        movie, TmdbDetails(keywords=tuple(keywords), companies=tuple(companies), original_language=language)
    )


def run(f, categories=(ANIMATION, FILMS), **kw):
    return score(f, list(categories), threshold=kw.pop("threshold", 0.8), margin=kw.pop("margin", 20), **kw)


def test_clear_animation_is_conclusive():
    result = run(facts(genres=["Animation", "Family"], companies=["Pixar Animation Studios", "Pixar"]))
    assert result.top == "animation"
    assert result.conclusive
    assert result.confidence == round(100 / 120, 3)
    assert {s["rule_id"] for s in result.signals} == {1, 3}


def test_no_animation_signal_goes_to_the_fallback():
    result = run(facts(genres=["Crime", "Thriller"]))
    assert (result.top, result.conclusive) == ("films", True)
    assert result.signals[-1]["kind"] == "fallback"


def test_a_single_weak_signal_is_held():
    result = run(facts(genres=["Animation", "Drama"]))
    assert result.top == "animation"
    assert not result.conclusive
    assert result.confidence < 0.8
    assert result.reasons[0]["code"] == "low_confidence"


def test_close_scores_are_held():
    result = run(facts(genres=["Animation"], keywords=["live action and animation"]), margin=30)
    assert not result.conclusive
    assert "close_second" in {r["code"] for r in result.reasons}


def test_comparison_ignores_case_and_accents():
    category = CategoryDef(9, "docs", "Docs", "", "/d", False, 1, (rule(9, "genre", "documentaire", 100),))
    result = run(facts(genres=["DOCUMENTAIRE"]), categories=(category,))
    assert result.top == "docs"
    result = run(facts(genres=["Documentaíre"]), categories=(category,))
    assert result.top == "docs"


def test_a_decisive_rule_settles_the_category():
    decisive = CategoryDef(
        3, "docs", "Docs", "", "/docs", False, 1, (rule(7, "genre", "Documentary", 10, decisive=True),)
    )
    result = run(facts(genres=["Documentary", "Animation"]), categories=(ANIMATION, FILMS, decisive))
    assert (result.top, result.confidence, result.conclusive, result.decisive) == ("docs", 1.0, True, "docs")


def test_two_decisive_rules_hold_the_movie():
    a = CategoryDef(3, "a", "A", "", "/a", False, 1, (rule(7, "genre", "Documentary", 10, decisive=True),))
    b = CategoryDef(4, "b", "B", "", "/b", False, 1, (rule(8, "genre", "Music", 10, decisive=True),))
    result = run(facts(genres=["Documentary", "Music"]), categories=(a, b))
    assert not result.conclusive
    assert result.reasons[0] == {"code": "decisive_conflict", "categories": ["a", "b"]}


def test_is_not_scores_when_the_value_is_absent():
    kids = CategoryDef(
        5, "kids", "Kids", "", "/k", False, 1, (rule(9, "certification", "R", 50, op="is_not"),)
    )
    assert run(facts(genres=["Comedy"]), categories=(kids,)).scores["kids"] == 50


def test_no_signal_and_no_fallback_is_held():
    result = run(facts(genres=["Crime"]), categories=(ANIMATION,))
    assert (result.top, result.conclusive, result.reasons) == (None, False, [{"code": "no_signal"}])


def test_the_ai_adds_a_weighted_signal():
    ai = AiVerdict(category="animation", confidence=0.9, reasoning="Hand-drawn animated feature")
    result = run(facts(genres=["Animation"]), ai=ai, ai_weight=60)
    assert result.scores["animation"] == 60 + 54
    assert result.conclusive
    assert result.signals[-1]["kind"] == "inference"


def test_an_unsure_ai_adds_nothing():
    ai = AiVerdict(category="unsure", confidence=0.4, reasoning="?")
    result = run(facts(genres=["Animation"]), ai=ai)
    assert result.scores["animation"] == 60
    assert not result.conclusive


def test_the_ai_never_overrides_a_decisive_rule():
    decisive = CategoryDef(
        3, "docs", "Docs", "", "/docs", False, 1, (rule(7, "genre", "Documentary", 10, decisive=True),)
    )
    ai = AiVerdict(category="animation", confidence=1.0, reasoning="looks animated")
    result = run(facts(genres=["Documentary", "Animation"]), categories=(ANIMATION, decisive), ai=ai)
    assert result.top == "docs"
    assert all(s["kind"] != "inference" for s in result.signals)


def test_category_snapshot_round_trip():
    assert CategoryDef.from_dict(ANIMATION.to_dict()) == ANIMATION
