from datetime import UTC, datetime

from triage.templates.render import Choice, HeldMovie, category_color, review_email

CHOICES = [Choice("films", "Films", 1), Choice("concerts", "Concerts", 3), Choice("shows", "Spectacles", 4)]


def movie(**values: object) -> HeldMovie:
    base: dict[str, object] = {
        "title": "We Will Rock You",
        "year": 1982,
        "poster_url": "https://image.tmdb.org/t/p/w342/p.jpg",
        "reasons": [{"code": "ai_only", "category": "concerts"}],
        "token": "tok",
        "suggested": "concerts",
        "scores": {"concerts": 160.0, "shows": 30.0},
        "excluded": {"films"},
        "ai": {"category": "concerts", "confidence": 1.0},
    }
    return HeldMovie(**{**base, **values})  # type: ignore[arg-type]


def render(locale: str = "fr", **values: object) -> tuple[str, str, str]:
    return review_email(locale, "http://t", [movie(**values)], CHOICES, datetime(2026, 1, 1, tzinfo=UTC))


def test_buttons_wear_their_category_color_and_the_suggested_one_is_filled():
    _, _, html = render()
    concerts = category_color(3)
    assert f"background:{concerts};color:#ffffff" in html
    assert f"background:#ffffff;color:{category_color(4)}" in html
    assert "Triage penche pour Concerts." in html


def test_each_choice_says_what_it_is_worth_like_the_review_page():
    _, text, html = render()
    assert "Concerts" in html and " · 76 % · IA 100 %" in html  # 160 / (160 + 30 + 20)
    assert " · 14 %" in html  # Spectacles: 30 / (30 + 160 + 20)
    assert " · exclu" in html  # Films ruled out
    assert "Déplacer vers Concerts · 76 % · IA 100 %: http://t/r/tok?c=concerts" in text


def test_the_poster_is_a_fixed_two_by_three_box():
    _, _, html = render()
    assert 'width="80" height="120"' in html and "object-fit:cover" in html
    _, _, without = render(poster_url=None)
    assert "<img" not in without


def test_reasons_are_written_out_never_as_their_code():
    _, text, html = render()
    assert "Seule l&#x27;IA a un avis" in html and "reason.ai_only" not in text + html
    _, text, _ = render(locale="en", reasons=[{"code": "decisive_conflict", "categories": ["A", "B"]}])
    assert "Several decisive rules disagree: A, B." in text
    _, text, _ = render(locale="en", reasons=[{"code": "brand_new"}])
    assert "Held for review." in text
