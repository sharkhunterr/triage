# Research: Triage MVP

Each entry: **Decision**, **Rationale**, **Alternatives considered**. Sources checked on
2026-11-08: Radarr's published OpenAPI (`src/Radarr.Api.V3/openapi.json`, develop) and a live
Radarr 6.2.1; Seerr's (Jellyseerr) `seerr-api.yml`, `server/routes/request.ts`, and
`server/subscriber/MediaRequestSubscriber.ts` (develop); Portalab's backend, frontend, Docker,
and CI configuration.

## R1. Finding the movies to sort — Radarr polling

- **Decision**: Poll `GET /api/v3/movie` (one call returns the whole library) and keep the
  movies whose `rootFolderPath` equals a configured intake folder. Root folders come from
  `GET /api/v3/rootfolder` (`id`, `path`, `accessible`, `freeSpace`). Default interval 5 min.
  A webhook (R6) only triggers an earlier poll.
- **Rationale**: Radarr is the source of truth for what sits in the intake folder (Constitution
  V); polling catches every movie whatever added it, survives missed webhooks, and makes
  processing restart-safe. One request per cycle is cheap even for libraries of thousands.
- **Alternatives**: Radarr "On Movie Added" webhook — fires before files exist and is lost if
  Triage is down; kept out of the MVP. Seerr webhooks as the only trigger — misses movies added
  directly in Radarr.

## R2. Moving a movie without breaking anything — Radarr movie editor

- **Decision**: `PUT /api/v3/movie/editor` with
  `{"movieIds": [id], "rootFolderPath": "<target>", "moveFiles": true}`. `deleteFiles` and
  `addImportExclusion` are never sent (explicitly `false`). After the call, re-read
  `GET /api/v3/movie/{id}` to confirm the new `rootFolderPath` before marking the decision
  done; Radarr moves existing files itself (`MoveMovieService`).
- **Rationale**: the editor changes only the root folder and keeps the folder name; it is the
  call the Radarr UI itself uses for "Move to root folder". The movie entry (id, tmdbId) is
  unchanged, so anything tracking it (Seerr) keeps working (Constitution I, V).
- **Alternatives**: `PUT /api/v3/movie/{id}?moveFiles=true` with a rewritten `path` —
  requires rebuilding the path ourselves and sending the whole resource back (risk of
  overwriting fields edited meanwhile). Delete and re-add — breaks Seerr tracking and history;
  forbidden.

## R3. Metadata signals — Radarr first, TMDB enrichment

- **Decision**: Radarr's `MovieResource` already carries `genres`, `keywords`, `studio`,
  `certification`, `originalLanguage`, `overview`, `year`, `tmdbId`, `remotePoster`. Triage
  uses them as the baseline signals. When a TMDB API key is set, it calls
  `GET https://api.themoviedb.org/3/movie/{tmdbId}?append_to_response=keywords,release_dates`
  to add the full `production_companies` list, TMDB genre ids (16 = Animation), the complete
  keyword list, and per-country certifications (`release_dates.results[].release_dates[]
  .certification`). Responses are cached per tmdbId for 7 days.
- **Rationale**: works without TMDB (degraded but useful: genre "Animation" alone settles most
  cases), and TMDB adds the decisive studio list (Radarr exposes only the main `studio`).
  One call per movie with `append_to_response` keeps TMDB usage minimal.
- **Alternatives**: TMDB only — a hard dependency for no gain; Radarr only — misses co-producing
  animation studios and region-specific certifications.

## R4. Local AI — Ollama structured output

- **Decision**: `POST {ollama}/api/chat` with `"stream": false`, `"format": <JSON schema>`
  (`{"category": enum of category keys + "unsure", "confidence": number 0–1, "reasoning":
  string}`), `"options": {"temperature": 0}`, and a timeout (default 60 s). The prompt lists
  each category's name and owner-written description, then the movie's title, year, overview,
  genres, keywords, and companies. The AI is only called when rules are not conclusive (no
  decisive rule matched and top confidence below threshold, or two categories close). Model
  list for the settings dropdown: `GET {ollama}/api/tags`.
- **Rationale**: JSON-schema `format` constrains the answer to a valid category or "unsure";
  temperature 0 keeps answers repeatable; calling it only for ambiguous movies keeps it off the
  hot path (Constitution IV). Default model suggestion: a 7–8B instruct model already common
  in the owner's homelab (e.g. `qwen3:8b`, `mistral:7b`).
- **Alternatives**: free-text answer parsed with regexes — brittle; an embeddings/RAG
  classifier (Classifarr's approach) — heavier and needs a vector store, contrary to XI.

## R5. Scoring model

- **Decision**: each rule `(field, operator, value, weight 1–100, decisive)` that matches adds
  its weight to its category's score. A decisive match settles the category unless another
  category also has a decisive match (→ hold). Confidence of the top category =
  `score_top / (score_top + score_second + k)` with `k` = 20 (a small prior so a single weak
  signal never reaches 80 %). The fallback category receives a base score when no other
  category has any signal. When consulted, the AI contributes a signal of weight
  `ai_weight × ai_confidence` (default `ai_weight` 60) to the category it chose; "unsure"
  contributes nothing. Move when confidence ≥ threshold (default 0.80) **and**
  `score_top − score_second ≥ margin` (default 20); otherwise hold.
- **Rationale**: transparent arithmetic the UI can explain line by line (Constitution III),
  deterministic for rules (IV), tunable without code (II). The preset's weights make clear
  cases pass alone (Animation genre 60 + an animation studio 40 → 100/120 = 0.83).
- **Alternatives**: a trained classifier — needs labelled data and is opaque; letting the AI
  decide alone — violates IV.

## R6. Seerr (Overseerr/Jellyseerr) — keeping requests intact

- **Findings**: Seerr links a request to Radarr through `media.tmdbId` and the Radarr movie id
  it stored when sending (`externalServiceId`); availability comes from its Radarr and media
  server sync jobs, by id, not by path. `PUT /api/v1/request/{id}` (body: `mediaType`,
  `serverId`, `profileId`, `rootFolder`, `userId`) is refused with **409 "Only pending
  requests can be modified"** unless the request is still pending; every request update runs
  `afterUpdate → sendToRadarr`.
- **Decision**: (1) Never remove/re-add a movie (R2): this alone keeps every approved request
  tracking its movie. (2) Movies in the intake folder belong to approved requests, which Seerr
  will not let anyone edit; Triage therefore does **not** try to edit them and records
  "request kept (approved, same Radarr entry)". (3) Optional webhook: Seerr's webhook agent
  posts JSON for `MEDIA_APPROVED` / `MEDIA_AUTO_APPROVED` (template fields
  `notification_type`, `media.tmdbId`, `media.media_type`, `request.request_id`); Triage
  validates a shared secret header and starts an immediate poll. (4) Seerr connection
  (URL + API key) is optional and used to show the requester and request status on a
  decision, and to check that tracked requests still resolve after a move (FR-022g becomes a
  verification, not an edit).
- **Rationale**: editing approved requests is impossible, and editing pending ones would make
  Triage act before the owner approved anything; verifying instead of editing satisfies the
  user's "don't break Seerr requests" with zero risk of re-sending to Radarr.
- **Alternatives**: pre-sorting pending requests by editing their `rootFolder` before approval
  — possible (pending only) and attractive, but it acts before the admin's approval and
  depends on approval not overriding the folder; noted as a follow-up feature.
- **Spec impact**: FR-022g is satisfied as "verify and record request tracking; edit only when
  the portal allows it (pending), which the MVP does not need". Recorded in plan Complexity
  Tracking as a clarification, not a deviation.

## R7. Email and one-click links

- **Decision**: `aiosmtplib` (STARTTLS/SSL, optional auth), one HTML + text email per
  processing run listing held movies with poster, reasons, and links
  `GET {base_url}/r/{token}?c={category_id}` (or `?c=intake`). Tokens are 32 random bytes,
  stored as SHA-256 hashes with expiry (default 7 days) and a used flag; the link opens a
  confirmation page that performs the choice with a POST (mail scanners that prefetch GET
  links must not trigger moves).
- **Rationale**: random single-use tokens need no signing library and can be revoked when the
  movie is decided elsewhere (Constitution VII); GET-then-POST protects against link
  prefetching.
- **Alternatives**: HMAC-signed stateless links — cannot be made single-use without storage
  anyway; magic-link auth to the whole UI — broader than needed.

## R8. Authentication

- **Decision**: one owner account created on first start (setup screen, LAN only until set).
  Password hashed with `argon2-cffi` (as in Portalab). Server-side sessions in SQLite, cookie
  `HttpOnly`, `SameSite=Lax`, `Secure` when served over HTTPS; state-changing API calls
  require the session plus an `X-Requested-With`-style CSRF header. Login rate limiting in
  memory (5 attempts/min/IP).
- **Rationale**: matches Portalab's approach at the smallest scale; no external identity
  provider for a single-owner tool.
- **Alternatives**: HTTP basic auth — no logout, poor on mobile; OIDC — overkill for MVP.

## R9. Background work in one process

- **Decision**: an asyncio worker started in FastAPI's lifespan: a poll loop (interval or
  webhook wake-up), a work table in SQLite (`work_item`: kind, movie, state, attempts,
  `next_attempt_at`, last_error) processed one item at a time, exponential backoff (1 min →
  2 → 4 … capped at 1 h, max 8 attempts), and scans as work items with progress. Outbound
  calls go through one `httpx.AsyncClient` per service with timeouts and a small
  concurrency limit (TMDB ≤ 4 req/s).
- **Rationale**: single image, SQLite, no Redis/queue (XI); persisting work items makes
  restarts safe and retries visible (V, VI).
- **Alternatives**: APScheduler/Celery — extra infrastructure; Portalab's PostgreSQL
  `SKIP LOCKED` jobs — needs PostgreSQL.

## R10. Idempotency key

- **Decision**: an *arrival* is `(radarr_movie_id, intake_root_folder_path, first_seen_at)`.
  A movie present in an intake folder with no open arrival creates one; an arrival is closed
  when the movie leaves the intake folder (by Triage or anyone). Decisions belong to an
  arrival; a movie returning to intake later (owner moved it back) creates a new arrival but
  is flagged "corrected" and never auto-sorted again (FR-021).
- **Rationale**: one decision per arrival survives restarts and repeated polls (FR-004) while
  allowing legitimate re-arrivals.

## R11. Frontend stack details (Portalab-aligned)

- **Decision**: React 19 + Vite 7 + TypeScript 5.9; TanStack Query for server state; React
  Router; Radix UI primitives + Tailwind 4 on CSS-variable tokens (light/dark); lucide-react;
  **react-intl** for EN/FR (Portalab's choice); Biome; Vitest + Testing Library; Playwright +
  `@axe-core/playwright` for e2e and accessibility at 360 px and 1280 px widths. The API
  client is typed from the backend's generated `openapi.json` (`openapi-typescript`), with a
  drift check in CI as in Portalab.
- **Rationale**: same toolchain as Portalab (shared habits, copy-paste-able configs);
  mobile-first layout with a bottom tab bar on phones and a sidebar on desktop.

## R12. Packaging and CI

- **Decision**: multi-stage Dockerfile (node:22-alpine builds the frontend; python:3.12-slim
  with `uv sync --frozen --no-dev`), the frontend served as static files by FastAPI, data in
  `/config` (SQLite, logs), entrypoint honouring `PUID`/`PGID`/`UMASK` (Pressarr v0.2.0
  pattern), healthcheck on `/healthz`. GitLab CI: validate (ruff, mypy, Biome, typecheck,
  openapi drift), test (pytest, vitest), build (image), publish (Docker Hub on tags),
  release notes from `GITHUB_RELEASES.md`.
- **Rationale**: mirrors Portalab and Pressarr pipelines, scaled down (no PostgreSQL service).
