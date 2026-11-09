# v0.3.1

## 🎬 Triage 0.3.1 — up-to-date screenshots, an icon for Unraid

### 📚 Documentation

- **Screenshots** — the README and the Docker Hub page show the new dashboard and the paged review
  queue, on desktop and on a phone.
- **An icon for Unraid** — the app icon as PNG (and JPEG), 512 px, to use as the template's
  *Icon URL*: `https://raw.githubusercontent.com/sharkhunterr/triage/main/docs/images/icon.png`.
  The README tells the Unraid mapping (`/config`, port 9393, `PUID=99`, `PGID=100`).

### Closed issues

#### Documentation and tooling

- `doc` The README's screenshots follow the new dashboard and review queue, and the app icon is
  published as PNG and JPEG for Unraid.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.3.1
```

# v0.3.0

## 🎬 Triage 0.3.0 — a dashboard at a glance, a review queue that scales

### ✨ Features

- **A new dashboard** — what waits for you comes first, with *Decide* and *Apply the confident
  proposals* (or *All sorted* when nothing waits). Four figures follow, this week's against the week
  before. The last 30 days are drawn a bar a day, Triage's own moves apart from yours. Each library
  shows how full it is in its category's colour, the services' state sits beside it, and the latest
  decisions come as a compact list.
- **To review, a page at a time** — both tabs (held movies and proposals) come in pages of 12, 24,
  48 or 96 movies, the size remembered. Hundreds of proposals no longer load at every look.
  *Decide all* loads the whole queue only when its window opens.
- **Back where you came from** — a movie's sheet goes back to the page it was opened from: the
  dashboard, To review at the same page, the activity, the history with its filters, a scan.

### 🐛 Fixes

- **Overseerr and Jellyseerr alike** — checking a request no longer fails with « HTTP 400 » on
  Overseerr: Triage only asks what both know, and a series sharing a movie's TMDB id is never taken
  for it. A service's refusal now shows its own message.

### Closed issues

#### Fixed

- `bug` Checking a request failed with « Seerr: answered HTTP 400 » on Overseerr — it works with
  Overseerr and Jellyseerr alike.
- `bug` A movie's sheet always went back to the history — it goes back to the page it was opened
  from.

#### New

- `feat` To review: pages and a number of movies per page, on both tabs.
- `feat` A more modern dashboard: what waits first, the week's trend, the last 30 days, the
  libraries and the services.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.3.0
```

# v0.2.0

## 🎬 Triage 0.2.0 — is it the right movie?

### ✨ Features

- **TMDB stills on the movie sheet** — up to eight backdrops (textless ones first) and a link to
  the TMDB page, to see at a glance whether Radarr matched the right movie. Tap a still to open it
  full size. Read from the TMDB cache; without TMDB the sheet shows as before.

### Closed issues

#### New

- `feat` Movie sheet: TMDB stills to check the match — the sheet shows a strip of TMDB backdrops
  and a link to the movie's TMDB page.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.2.0
```

# v0.1.0

## 🎬 Triage 0.1.0 — first release

Triage sorts newly requested movies into the right Radarr library. Requests from Overseerr or
Jellyseerr land in an intake root folder; Triage scores each movie against your own categories, asks
a local AI (Ollama) when the rules are not conclusive, and moves it — or keeps it aside and asks you.

### ✨ Features

- **Setup wizard** — Radarr, intake folder, libraries, then optional TMDB, Ollama, email and
  Overseerr/Jellyseerr, each with a *Test* button; run it again any time from Settings.
- **Your own categories** — name, Radarr library, description for the AI and weighted rules on
  genres, keywords, production companies, age ratings and original language. A rule can add points,
  settle the category (*decisive*) or **exclude** it. A *Movies / Animation* preset to start: adult
  content (keywords, R / 16 / 18 ratings), horror and thrillers stay out of Animation, live action
  remakes go to Movies.
- **A local AI that knows your rules** — Ollama reads each category's folder, rules and exclusions
  and what the rules found, then answers in your language. Ask it when the rules are unsure,
  always (a second opinion), or never.
- **Preview mode by default** — Triage proposes; apply one proposal, the confident ones, or decide
  every waiting movie in one dialog. Switch to automatic when you trust it.
- **Analyze** — one movie from its page, or the intake folder: everything, the movies waiting for
  a decision, or the new ones only. **Scans** classify a whole library; proposals only.
- **Activity** — every analysis and move, live, step by step (Radarr, metadata, rules, AI,
  decision), with a progress indicator on every page.
- **Explainable decisions** — the movie sheet (synopsis, genres, companies, rating, keywords) in
  the color of the category each value counted for, points per category, the AI's opinion apart.
- **Undo** — put a move back, or every move of a period, exactly where the movie came from; the
  movie waits for you again and is never sorted on its own.
- **Doubt is never a move** — doubtful movies wait in the review queue; one email per run with
  single-use, expiring one-click links.
- **Requests keep working** — moves go through Radarr's movie editor (same movie entry); Seerr
  requests are checked, never edited. The Seerr webhook sorts a request within seconds.
- **TMDB in your language** — titles, synopsis and your country's age ratings.
- Mobile and desktop, English and French, light and dark themes.

### 🐳 Quick start

```yaml
services:
  triage:
    image: sharkhunterr/triage:0.1.0
    ports: ["9393:9393"]
    volumes: ["./config:/config"]
    environment: [TZ=Europe/Paris, PUID=1000, PGID=1000]
```
