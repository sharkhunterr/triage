from tests.unit.test_scoring import ANIMATION_NO_HORROR, FILMS, facts
from triage.domain.ai_prompt import DEFAULT_INSTRUCTIONS, build_prompt
from triage.domain.scoring import score


def test_the_ai_sees_each_category_with_its_folder_and_rules():
    system, _ = build_prompt(facts(genres=["Animation"]), [ANIMATION_NO_HORROR, FILMS])
    assert "/media/animation" in system
    assert "genre is Animation (+60, decisive)" in system
    assert "Never when: genre is Horror; genre is Thriller" in system
    assert "live action" in system and "(fallback" in system
    assert "never choose a category ruled out" in system.lower()
    assert "written in English" in system
    french, _ = build_prompt(facts(genres=["Animation"]), [ANIMATION_NO_HORROR, FILMS], language="fr-FR")
    assert "written in French" in french


def test_the_ai_judges_on_the_listed_facts_only():
    """A small model otherwise assumes a genre the movie does not have (a live-action film "is
    animated"). The length of its reasoning is the owner's call, not a fixed limit."""
    system, _ = build_prompt(facts(genres=["Comedy"]), [ANIMATION_NO_HORROR, FILMS])
    assert "counts only if it is listed" in system
    assert "300 characters" not in system and "two sentences" not in system


def test_the_owners_instructions_replace_the_default_but_keep_the_categories():
    custom = "Tri de films. Réponds en {language}. {not a placeholder}"
    system, _ = build_prompt(facts(genres=["Comedy"]), [ANIMATION_NO_HORROR, FILMS], instructions=custom)
    assert system.startswith("Tri de films. Réponds en English. {not a placeholder}")
    assert "/media/animation" in system  # the categories are always appended
    blank, _ = build_prompt(facts(genres=["Comedy"]), [ANIMATION_NO_HORROR, FILMS], instructions="  ")
    assert blank.startswith(DEFAULT_INSTRUCTIONS.split("\n")[0])  # blank means the default


def test_the_ai_sees_what_is_ruled_out_but_not_the_points():
    """A second opinion, not an echo: the exclusions are the owner's hard rules, the tally is not shown."""
    movie = facts(genres=["Animation", "Thriller"])
    result = score(movie, [ANIMATION_NO_HORROR, FILMS], threshold=0.8, margin=20)
    _, user = build_prompt(movie, [ANIMATION_NO_HORROR, FILMS], result)
    assert "- animation (genre is Thriller)" in user
    assert "points" not in user
    _, clear = build_prompt(facts(genres=["Crime"]), [ANIMATION_NO_HORROR, FILMS], result=None)
    assert "Ruled out" not in clear
