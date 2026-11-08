# Contract: Triage HTTP API (`/api/v1`)

JSON over HTTPS/HTTP. All endpoints except those marked *public* require a valid session
cookie; state-changing calls (POST/PUT/PATCH/DELETE) also require the header
`X-Triage-CSRF: 1`. Errors use `{"error": {"code": str, "message": str, "details": {}}}` with
4xx/5xx. The backend publishes the full schema as `openapi.json`; the frontend client is
generated from it.

## Auth & setup

| Method | Path | Notes |
|---|---|---|
| GET | `/setup/status` *public* | `{ "needs_setup": bool }` |
| POST | `/setup` *public, only while no owner* | `{username, password, locale}` → creates owner, opens session |
| POST | `/auth/login` *public* | `{username, password}` → 204 + cookie; 429 after 5 failures/min |
| POST | `/auth/logout` | 204 |
| GET | `/auth/me` | `{username, locale}` |

## Settings & connections

| Method | Path | Notes |
|---|---|---|
| GET | `/settings` | all settings; secrets as `{ "set": bool }` |
| PATCH | `/settings` | partial update; secrets write-only; validates folders against Radarr |
| POST | `/settings/test/{service}` | `service` ∈ `radarr, tmdb, ollama, seerr, smtp` → `{ok, detail, latency_ms}`; may use unsaved values from the body |
| GET | `/radarr/root-folders` | `[{path, accessible, free_space}]` for pickers |
| GET | `/ollama/models` | `[name]` from Ollama `/api/tags` |

## Categories

| Method | Path | Notes |
|---|---|---|
| GET | `/categories` | with rules, ordered |
| POST | `/categories` | create (validation per data-model) |
| PUT | `/categories/{id}` | replace (name, description, root folder, fallback, rules) → `version`+1 |
| DELETE | `/categories/{id}` | soft delete; 409 if it is the only category |
| POST | `/categories/reorder` | `{ids: [...]}` |
| GET | `/presets` | available presets (`movies-animation`) |
| POST | `/presets/{key}/apply` | creates the preset's categories; root folders left to choose |

## Decisions, review, preview

| Method | Path | Notes |
|---|---|---|
| GET | `/dashboard` | counts (moved, held, proposed, failed, today/7 days), latest 10 decisions, mode |
| GET | `/decisions` | filters `status, category, source, q, from, to`, cursor pagination |
| GET | `/decisions/{id}` | full detail: signals (facts), AI (inference), scores, snapshot, request check, audit trail |
| POST | `/decisions/{id}/apply` | for `proposed`/`held`: body `{category_id}` or `{"target": "intake"}` |
| POST | `/decisions/{id}/dismiss` | `proposed` → `dismissed` |
| POST | `/decisions/{id}/correct` | for `moved`: `{category_id}` or `{"target": "intake"}`; sets `movie_ref.corrected` |
| POST | `/decisions/apply-confident` | applies all `proposed` with confidence ≥ threshold (optional `scan_id`) → `{applied: n}` |
| POST | `/movies/{radarr_id}/simulate` | returns a decision with `status: simulated`; never moves |
| GET | `/review` | `held` + `proposed` decisions, oldest first |

## Scans

| Method | Path | Notes |
|---|---|---|
| POST | `/scans` | `{root_folder_path}` → `scan` (202); 409 if a scan is running |
| GET | `/scans` / `/scans/{id}` | state, progress, counts |
| GET | `/scans/{id}/results` | proposals: current folder, proposed category, confidence, in place or not |
| POST | `/scans/{id}/cancel` | keeps partial results |

## Status & operations

| Method | Path | Notes |
|---|---|---|
| GET | `/status` | per service `{state: ok|degraded|down|disabled, detail, checked_at}`, last/next poll, queue counts, failed items, category folder warnings (FR-022h) |
| POST | `/poll` | trigger an immediate poll |
| POST | `/work-items/{id}/retry` | retry a failed item |
| GET | `/healthz` *public* | liveness (no dependency checks) |

## Inbound webhook (*public, secret-protected*)

`POST /api/v1/webhooks/seerr` — header `Authorization: <seerr.webhook_secret>` (Seerr's
webhook agent "Authorization Header" field). Body: Seerr's JSON template; Triage reads only
`notification_type` and `media.media_type`. On `MEDIA_APPROVED` or `MEDIA_AUTO_APPROVED` for
`movie`: 202 and an immediate poll; `TEST_NOTIFICATION`: 204; anything else: 204 ignored;
wrong secret: 401, nothing processed.

## Email decision links (*public, token-protected*)

| Method | Path | Notes |
|---|---|---|
| GET | `/r/{token}?c={category_key|intake}` | HTML confirmation page (movie, chosen category); never acts on GET (mail-scanner prefetch) |
| POST | `/r/{token}` | `c` in form body; performs the choice; marks token used; 410 if used/expired/revoked, with a link to the review queue |
