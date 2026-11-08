# Quickstart: Triage MVP

Validates the feature end to end against a real (test) Radarr. Every step maps to a user
story; nothing here touches a production library.

## 1. Run Triage

```bash
docker run -d --name triage -p 9393:9393 \
  -e PUID=1000 -e PGID=1000 -e TZ=Europe/Paris \
  -v ./config:/config \
  sharkhunterr/triage:latest
```

Development instead: `cd backend && uv sync && uv run triage serve --reload` and
`cd frontend && npm ci && npm run dev` (Vite proxies `/api` to the backend).

## 2. Test Radarr

Use a disposable Radarr (the homelab's `classifarr-test-radarr` on :7878 already has root
folders `/data/media/films` and `/data/media/dessin-anime`). Add a third root folder
`/data/media/nouveaux` as the intake folder, then add, with root folder `nouveaux`:

| Movie | Expected |
|---|---|
| Toy Story (1995, tmdb 862) | Dessins Animés — genre Animation + Pixar |
| Heat (1995, tmdb 949) | Films — no animation signal, fallback |
| Who Framed Roger Rabbit (1988, tmdb 856) | held — live action + animation |
| Perfect Blue (1997, tmdb 10494) | AI decides; held if the owner's category description excludes adult animation |

## 3. First start (US3, US8)

1. Open http://localhost:9393, create the owner account.
2. Settings: Radarr URL + key → **Test**; intake folder `/data/media/nouveaux`; TMDB key →
   **Test**; Ollama URL + model → **Test** (optional); SMTP → **Test** (optional).
3. Categories: apply the **Movies / Animation** preset, pick `/data/media/dessin-anime` for
   *Dessins Animés* and `/data/media/films` for *Films* (fallback).

## 4. Preview and scan (US4, US5)

1. Mode stays **Preview**. Start a **Scan** of the intake folder.
2. Expect proposals: Toy Story → Dessins Animés, Heat → Films, Roger Rabbit → held, nothing
   moved in Radarr (check its UI).
3. Open Toy Story's proposal: signals listed as facts, AI reasoning (if called) labelled as
   inference, confidence ≥ 80 %.
4. **Apply all confident** → Toy Story and Heat move in Radarr; Roger Rabbit stays.

## 5. Automatic mode and review (US1, US2)

1. Switch to **Automatic**. Add *Coco* (tmdb 354912) to the intake folder, click **Check now**
   (or wait ≤ 5 min): it is moved to Dessins Animés without any action.
2. Add a doubtful movie: it stays, appears in **Review**, and one email arrives with one link
   per category. Open a link → confirmation page → confirm → moved; open it again → "already
   decided".

## 6. Corrections and safety (US7, edge cases)

1. Correct Coco back to the intake folder from its decision → moved back, marked corrected,
   never auto-sorted again on the next polls.
2. Stop Ollama, add a new movie → decided on rules alone or held; status page shows Ollama
   down; no move with low confidence.
3. Stop Radarr during a poll → work items retried; status page shows Radarr down; no crash.

## 7. Requests (US6, US9)

With Jellyseerr/Overseerr connected to the same Radarr: request a movie as a non-admin user,
approve it, configure the webhook (`POST /api/v1/webhooks/seerr`, Authorization header =
Triage's webhook secret). Triage polls within seconds, moves the movie, and the decision shows
"request tracked"; in Seerr the request still shows the movie and becomes available once
downloaded.

## 8. Quality gates

```bash
cd backend && uv run ruff check . && uv run mypy && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm test && npx playwright test
```
