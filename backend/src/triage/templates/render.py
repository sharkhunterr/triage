"""HTML for the review email and the one-click link pages. Everything is escaped."""

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any

from triage.domain.scoring import PRIOR
from triage.templates.messages import reason_text, text

ACCENT = "#5b4bdb"
# the web interface's category colors (light theme), picked by category id the same way
CATEGORY_COLORS = ("#6d28d9", "#0f766e", "#b45309", "#1d4ed8", "#be185d", "#15803d")


@dataclass
class HeldMovie:
    title: str
    year: int | None
    poster_url: str | None
    reasons: list[dict[str, Any]]
    token: str
    suggested: str | None = None  # the key of the category the rules lean to
    scores: dict[str, float] = field(default_factory=dict)
    excluded: set[str] = field(default_factory=set)
    ai: dict[str, Any] | None = None


@dataclass
class Choice:
    key: str
    name: str
    id: int = 0


def category_color(category_id: int) -> str:
    return CATEGORY_COLORS[(category_id - 1) % len(CATEGORY_COLORS)]


def _label(movie: HeldMovie) -> str:
    return f"{movie.title} ({movie.year})" if movie.year else movie.title


def _confidence(movie: HeldMovie, key: str) -> float:
    """What the rules give this category against the best other one — the review page's figure."""
    own = movie.scores.get(key, 0.0)
    if key in movie.excluded or own <= 0:
        return 0.0
    best = max([0.0, *(v for k, v in movie.scores.items() if k != key)])
    return own / (own + best + PRIOR)


def _worth(locale: str, movie: HeldMovie, key: str) -> str:
    """« · 76 % · IA 100 % », or « · exclu »."""
    if key in movie.excluded:
        return f" · {text(locale, 'email.excluded')}"
    worth = f" · {round(_confidence(movie, key) * 100)} %"
    ai = movie.ai or {}
    if not ai.get("error") and ai.get("category") == key and ai.get("confidence") is not None:
        worth += f" · {text(locale, 'email.ai')} {round(float(ai['confidence']) * 100)} %"
    return worth


def _button(label: str, url: str, color: str, filled: bool) -> str:
    style = (
        f"background:{color};color:#ffffff;border:1px solid {color}"
        if filled
        else f"background:#ffffff;color:{color};border:1px solid {color}"
    )
    return (
        f'<a href="{escape(url)}" style="display:inline-block;margin:6px 6px 0 0;padding:8px 12px;'
        f'border-radius:8px;{style};text-decoration:none;font-size:14px;line-height:18px">{label}</a>'
    )


def _poster(movie: HeldMovie) -> str:
    # fixed 2:3 box, as TMDB posters are: no client can stretch it
    if not movie.poster_url:
        return '<div style="width:80px;height:120px;border-radius:8px;background:#eef0f6"></div>'
    return (
        f'<img src="{escape(movie.poster_url)}" alt="" width="80" height="120" '
        'style="display:block;width:80px;height:120px;object-fit:cover;border-radius:8px;border:0">'
    )


def review_email(
    locale: str, base_url: str, movies: list[HeldMovie], choices: list[Choice], expires: datetime
) -> tuple[str, str, str]:
    """Subject, plain text, HTML."""
    subject = text(locale, "email.subject", count=len(movies))
    date = expires.strftime("%Y-%m-%d")
    lines = [text(locale, "email.intro"), ""]
    blocks = []
    for movie in movies:
        reasons = [reason_text(locale, r) for r in movie.reasons]
        leave = f"{base_url}/r/{movie.token}?c=intake"
        moves = [(c, f"{base_url}/r/{movie.token}?c={c.key}", _worth(locale, movie, c.key)) for c in choices]
        lines += [
            f"• {_label(movie)}",
            *[f"  {r}" for r in reasons],
            *[f"  {text(locale, 'email.moveTo', category=c.name)}{worth}: {url}" for c, url, worth in moves],
            f"  {text(locale, 'email.leave')}: {leave}",
            "",
        ]
        buttons = "".join(
            _button(
                f'{escape(c.name)}<span style="font-size:12px">{escape(worth)}</span>',
                url,
                category_color(c.id),
                c.key == movie.suggested,
            )
            for c, url, worth in moves
        )
        buttons += _button(escape(text(locale, "email.leave")), leave, "#5a6275", False)
        suggested = next((c for c in choices if c.key == movie.suggested), None)
        hint = (
            f'<p style="margin:4px 0 0;font-size:13px">'
            f"{escape(text(locale, 'email.suggested', category=suggested.name))}</p>"
            if suggested
            else ""
        )
        blocks.append(
            '<tr><td style="padding:16px 0;border-top:1px solid #dde1ea">'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td width="80" valign="top" style="width:80px;padding-right:12px">{_poster(movie)}</td>'
            f'<td valign="top"><strong style="font-size:15px">{escape(_label(movie))}</strong>{hint}'
            f'<ul style="margin:4px 0 0;padding-left:18px;color:#5a6275;font-size:13px">'
            f"{''.join(f'<li>{escape(r)}</li>' for r in reasons)}</ul></td></tr>"
            f'<tr><td colspan="2" style="padding-top:6px">{buttons}</td></tr></table></td></tr>'
        )
    lines += [f"{text(locale, 'email.openApp')}: {base_url}/review", text(locale, "email.footer", date=date)]
    html = (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;'
        'margin:auto;color:#121624">'
        f"<h2>{escape(subject)}</h2><p>{escape(text(locale, 'email.intro'))}</p>"
        f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0">{"".join(blocks)}</table>'
        f'<p style="margin-top:16px">{_button(escape(text(locale, "email.openApp")), f"{base_url}/review", ACCENT, True)}</p>'
        f'<p style="color:#5a6275;font-size:12px">{escape(text(locale, "email.footer", date=date))}</p></div>'
    )
    return subject, "\n".join(lines), html


def page(locale: str, title: str, body: str, *, form: str = "", link: str = "") -> str:
    return f"""<!doctype html>
<html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} — Triage</title>
<style>
body{{font-family:system-ui,sans-serif;background:#f6f7fb;color:#121624;margin:0;display:flex;min-height:100vh;
align-items:center;justify-content:center;padding:16px}}
main{{background:#fff;border:1px solid #dde1ea;border-radius:16px;padding:24px;max-width:420px;width:100%}}
button,a.btn{{display:inline-block;background:{ACCENT};color:#fff;border:0;border-radius:10px;padding:12px 18px;
font-size:16px;text-decoration:none;cursor:pointer}}
@media (prefers-color-scheme:dark){{body{{background:#0d1017;color:#e8ebf3}}main{{background:#151a24;
border-color:#2a3242}}}}
</style></head>
<body><main><h1 style="font-size:20px">{escape(title)}</h1><p>{escape(body)}</p>{form}{link}</main></body></html>"""


def confirm_form(choice: str, label: str) -> str:
    return (
        f'<form method="post"><input type="hidden" name="c" value="{escape(choice)}">'
        f'<button type="submit">{escape(label)}</button></form>'
    )


def app_link(base_url: str, label: str) -> str:
    return f'<p><a class="btn" href="{escape(base_url)}/review">{escape(label)}</a></p>'
