"""HTML for the review email and the one-click link pages. Everything is escaped."""

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Any

from triage.templates.messages import reason_text, text

ACCENT = "#5b4bdb"


@dataclass
class HeldMovie:
    title: str
    year: int | None
    poster_url: str | None
    reasons: list[dict[str, Any]]
    token: str


@dataclass
class Choice:
    key: str
    name: str


def _label(movie: HeldMovie) -> str:
    return f"{movie.title} ({movie.year})" if movie.year else movie.title


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
        links = [
            (text(locale, "email.moveTo", category=c.name), f"{base_url}/r/{movie.token}?c={c.key}")
            for c in choices
        ]
        links.append((text(locale, "email.leave"), f"{base_url}/r/{movie.token}?c=intake"))
        lines += [
            f"• {_label(movie)}",
            *[f"  {r}" for r in reasons],
            *[f"  {label}: {url}" for label, url in links],
            "",
        ]
        poster = (
            f'<img src="{escape(movie.poster_url)}" alt="" width="60" style="border-radius:6px;margin-right:12px">'
            if movie.poster_url
            else ""
        )
        buttons = "".join(
            f'<a href="{escape(url)}" style="display:inline-block;margin:4px 6px 0 0;padding:8px 12px;'
            f"border-radius:8px;background:{ACCENT if i < len(choices) else '#eef0f6'};"
            f'color:{"#fff" if i < len(choices) else "#121624"};text-decoration:none;font-size:14px">'
            f"{escape(label)}</a>"
            for i, (label, url) in enumerate(links)
        )
        blocks.append(
            '<tr><td style="padding:12px 0;border-top:1px solid #dde1ea">'
            f'<div style="display:flex">{poster}<div><strong>{escape(_label(movie))}</strong>'
            f'<ul style="margin:4px 0;padding-left:18px;color:#5a6275;font-size:13px">'
            f"{''.join(f'<li>{escape(r)}</li>' for r in reasons)}</ul>{buttons}</div></div></td></tr>"
        )
    lines += [f"{text(locale, 'email.openApp')}: {base_url}/review", text(locale, "email.footer", date=date)]
    html = (
        '<div style="font-family:system-ui,sans-serif;max-width:640px;margin:auto;color:#121624">'
        f"<h2>{escape(subject)}</h2><p>{escape(text(locale, 'email.intro'))}</p>"
        f'<table width="100%" cellspacing="0">{"".join(blocks)}</table>'
        f'<p><a href="{escape(base_url)}/review" style="color:{ACCENT}">{escape(text(locale, "email.openApp"))}</a></p>'
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
