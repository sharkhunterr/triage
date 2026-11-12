# v0.8.0

## 🎬 Triage 0.8.0 — choose whether the AI thinks before its verdict

### ✨ Features

- **Think before answering** — a new switch in Settings › AI. Off (the default), the model gives a
  short verdict, the fastest. On, it reasons before it answers: closer on hard cases, but several
  times slower, minutes per movie without a graphics card, so raise the timeout (up to 600 s).
  gpt-oss then uses its medium reasoning level, and the answer leaves room for the reasoning so the
  verdict is never cut off.

### Closed issues

#### Fixed

- `bug` A switch's description is no longer read as part of its name by screen readers.

#### New

- `feat` Choose whether the AI thinks before its verdict.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.8.0
```

# v0.7.0

## 🎬 Triage 0.7.0 — lighter AI calls, ready for a CPU-only Ollama, the model picked from a list

### ✨ Features

- **Lighter AI calls** — Triage asks Ollama for a short verdict without a long reasoning pass
  (thinking off, a capped answer, a fixed context), so a full analysis or a check no longer keeps
  the GPU or the CPU busy for minutes on each movie. gpt-oss, which cannot turn its reasoning off,
  uses its lowest reasoning level.
- **Ready for a CPU-only Ollama** — the model stays loaded 30 minutes between a batch's movies, and
  the AI timeout now defaults to 180 s. A timeout saved earlier keeps its value: raise it in
  Settings › AI if your Ollama runs on the CPU.
- **The AI model is picked from a list** — Settings and the setup wizard list the models installed
  at the Ollama address once it answers (saved and reachable, or just tested). The address alone is
  enough to test Ollama; the AI waits until a model is chosen.

### Closed issues

#### Fixed

- `bug` gpt-oss answered empty when its reasoning was turned off: it now uses its lowest reasoning
  level.

#### New

- `feat` Lighter Ollama requests: thinking off, a capped answer, a fixed context.
- `feat` A CPU-only Ollama works out of the box: the model stays loaded between a batch's movies and
  the AI timeout defaults to 180 s.
- `feat` The AI model is picked from the models installed at the Ollama address.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.7.0
```

# v0.6.0

## 🎬 Triage 0.6.0 — stop work from the Activity page

### ✨ Features

- **Stop what runs or waits** — the Activity page lists what waits, by group: a library check,
  the movie analyses (a full analysis or the new movies), the title updates, the Seerr requests.
  Each group has *Stop*, the job running now has its own, and *Stop all* stops everything at once.
  The job running now is interrupted even while the AI thinks, and what it had started is not kept.
- **Nothing is lost** — a stopped movie stays where it is: a new movie is counted among the new
  ones to analyse later, and a stopped check keeps the results it already has. Moves and the review
  email are never stopped: they show as *always goes through*, so no movie is left half moved.
- **Cancel a check** on the Check page now does the same: its queued movies are dropped and the
  movie being checked is interrupted.

### Closed issues

#### New

- `feat` Stop running or queued work from the Activity page: a check, the analyses, the title
  updates, the Seerr requests; moves and emails always go through.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.6.0
```

# v0.5.0

## 🎬 Triage 0.5.0 — check any library, a library slider, locks, a History timeline

### ✨ Features

- **A Check tab** — check any library for movies that belong in another. A check moves nothing: it
  lists the gaps (a better library), the doubts and the movies already in place, and you settle them
  like the review queue. The tab's badge counts what is left to settle, and the check picker gives
  each check's count.
- **Choose on a library slider** — the review queue, the Check tab and the movie sheet share one
  control: one stop per library, a pin where the movie is, Triage's confidence over each stop (the
  chosen one in a badge, *ruled out* where a rule excludes it), the way to the library chosen in
  their colours. Slide or tap, then confirm; back on its own library, the movie stays there. On a
  movie already moved, the same slider corrects the move.
- **Locks** — a movie you sorted by hand (on its sheet, in the review queue, from the email, or in a
  check) is locked in its library. A check respects locks by default, or ignores them. Applying
  proposals in bulk never locks, undoing in bulk drops the lock. A discreet padlock shows the lock;
  on the sheet, its details and *Unlock* are one tap away.
- **History as a timeline** — grouped by day: each movie's poster with its status, where it went in
  the categories' colours, who decided, the lock, the hour, and Triage's confidence as a ring. Each
  day shows its libraries as a strip.

### 🐛 Fixes

- **A live-action/animated film is no cartoon** — when Wikidata says « live-action », Animation is
  ruled out and the film counts for Films. Animation also rules out Shows and Concerts.
- **In place means in place** — a movie whose best choice is the library it is in is counted as in
  place, sure or not.
- **A cleaner movie sheet** — *Why this decision* no longer repeats in a sentence what the score
  chips show, and the *Radarr and TMDB* box links to the movie on TMDB, like the Wikipedia one.

### Closed issues

#### Fixed

- `bug` Live-action/animated films no longer count as cartoons.
- `bug` The Check badge and the Check page agree: the page shows what the other checks still wait
  on, and the picker gives each check's count.

#### New

- `feat` A Check tab: check any library for movies that belong in another, settled like the review
  queue.
- `feat` A movie's library is locked after a choice made by hand; checks respect or ignore locks.
- `feat` A modern History: a timeline per day, and the same cards with a library slider in the
  review queue, the Check tab and on the movie sheet.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.5.0
```

# v0.4.1

## 🎬 Triage 0.4.1 — a clearer review email, a working email test

### 🐛 Fixes

- **The review email reads like the review page** — each button wears its category's colour, the
  category Triage leans to is filled, and each choice shows its percentage (and the AI's when it
  picked it). Posters keep their shape, and every reason is written out in full.
- **Testing the email works** — *Test* in Settings › Email no longer fails silently: the connection
  tries the mail server's addresses in turn, so one that stalls no longer costs the whole timeout.
  Every *Test* button shows that it is running, and why it failed.

### Closed issues

#### Fixed

- `bug` The review email shows each choice like the review page, and testing the email no longer
  times out or fails without a word.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.4.1
```

# v0.4.0

## 🎬 Triage 0.4.0 — Shows and Concerts, Wikidata and Wikipedia, a sharper AI

### ✨ Features

- **Shows and Concerts presets** — each adds one category beside the ones you already have: Shows
  (stand-up, one-man and one-woman shows, filmed plays, opera, ballet, circus) and Concerts (concert
  films, tours and festivals). They are offered even when categories exist.
- **Complete a preset** — when a preset gains rules, Categories offers *Complete « name »*: the
  categories made from it get the new rules. Your own changes stay as they are.
- **Wikidata and Wikipedia** (optional, Settings › Wikidata & Wikipedia, off by default) — Triage
  reads the movie's Wikidata kind of work and genre (concert film, stand-up comedy, biographical
  film…) and the opening of its Wikipedia article in the TMDB language. *Wikidata type* is a new rule
  field and the presets use it. The AI reads the article. The facts are cached with TMDB's, and an
  outage never holds an analysis.
- **A tidier movie sheet** — the metadata come grouped by source: Radarr and TMDB (synopsis, filled
  fields, what is missing), then Wikidata and Wikipedia (the opening, the type, a link). The sheet
  also shows who asked for the movie in Overseerr / Jellyseerr and when, or else when Radarr added it.
- **The dashboard's 30 days, three ways** — sorted (by Triage alone / by you), by category (in each
  category's colour) or analysed (sure / in doubt). The choice is remembered.
- **Refresh folders** — Settings › Radarr and the category editor read Radarr's root folders again,
  after a library was added or renamed there.

### 🐛 Fixes

- **The AI is a real second opinion** — a movie with no genre or keyword no longer falls into the
  default category when the AI clearly sees another one. It is proposed or held, never moved on the
  AI alone. The AI no longer sees the points the rules gave, only what you ruled out, and judges what
  the film actually is: a drama about a singer is no concert, and a one-woman show is a show.

### Closed issues

#### Fixed

- `bug` The AI is a real second opinion: the default category no longer outweighs it, the presets'
  rules are richer, and the AI judges the film rather than the rules' points.

#### New

- `feat` A movie's sheet: who asked for it in Seerr and when.
- `feat` Shows and Concerts presets, offered beside existing categories.
- `feat` Refresh Radarr's root folders from Settings and the category editor.
- `feat` The dashboard's 30-day chart by who sorted, by category, or analysed (sure / in doubt).
- `feat` Wikidata type as a rule field, Wikipedia opening for the AI and on the sheet.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.4.0
```

# v0.3.2

## 🎬 Triage 0.3.2 — up-to-date screenshots, an icon for Unraid

Everything 0.3.1 brought (it stayed on GitLab), now on Docker Hub and GitHub too.

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
- `doc` Releasing publishes reliably: `npm run release:full` after `npm run release` publishes that
  same version instead of making a new one, and publishing a tag again no longer fails on its
  existing release.

### 🐳 Update

```bash
docker pull sharkhunterr/triage:0.3.2
```

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
