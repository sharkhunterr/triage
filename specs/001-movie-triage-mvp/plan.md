# Implementation Plan: Triage MVP — sort newly requested movies into the right library

**Branch**: `001-movie-triage-mvp` | **Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-movie-triage-mvp/spec.md`

## Summary

Triage watches Radarr's intake root folder(s), classifies each new movie against the owner's
categories with weighted metadata rules (Radarr fields, enriched by TMDB) and, for ambiguous
cases only, a local Ollama model constrained to a JSON answer; it then moves the movie with
Radarr's movie editor (same entry, files moved by Radarr) or holds it for review with an email
of single-use decision links. Preview mode and folder scans produce proposals the owner
applies. A single FastAPI process (API, static React app, in-process worker over a SQLite work
table) ships as one Docker image. Seerr requests stay intact because the Radarr entry is never
recreated; Triage verifies tracking instead of editing requests (research R6).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.9 on Node 22 LTS (frontend)
**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2 async + aiosqlite, Alembic,
httpx, aiosmtplib, argon2-cffi, uvicorn; React 19, Vite 7, TanStack Query, React Router,
Radix UI, Tailwind 4, lucide-react, react-intl, openapi-typescript
**Storage**: SQLite file in `/config` (WAL mode); no other datastore
**Testing**: pytest + pytest-asyncio (unit, integration with fakes, contract tests for adapters
against recorded payloads), Vitest + Testing Library, Playwright + axe (360 px and 1280 px)
**Target Platform**: Linux container (amd64/arm64) on a homelab LAN; modern mobile and desktop
browsers
**Project Type**: web application (backend API + worker, frontend SPA) in one image
**Performance Goals**: intake movie decided ≤ 5 min after arrival (≤ 1 min with webhook);
scan of 500 movies ≤ 30 min with TMDB ≤ 4 req/s; UI pages interactive < 1 s on LAN
**Constraints**: never delete or move without confidence/owner action; secrets never sent to
the browser; works with TMDB, Ollama, Seerr, and SMTP all absent; < 250 MB RAM idle
**Scale/Scope**: one owner; libraries up to ~10 000 movies; ~10 screens; 5 external services

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Pre-design and post-design results (identical; design introduced no deviation):

- [x] **I. Safe automation** — moves only via `decision` state machine when confidence ≥
      threshold and margin met in automatic mode, or on owner action; `deleteFiles` hard-coded
      false; corrections and "leave in intake" supported; owner decisions win (FR-021).
- [x] **II. Configurable categories** — categories/rules are data; preset is a seed; decisions
      keep `categories_snapshot` with versions.
- [x] **III. Explainable decisions** — `signals` (facts) and `ai` (inference) stored separately
      and shown separately in decision detail and email.
- [x] **IV. Rules first, AI second** — scoring engine runs first; AI only when not conclusive;
      AI errors recorded and ignored; no cloud provider in scope.
- [x] **V. Source of truth** — Radarr polled as truth; arrivals give idempotency; movies leaving
      intake supersede pending work; only `rootFolderPath` changed via the editor.
- [x] **VI. Resilience** — persistent work items with exponential backoff; per-service health
      on `/status`; failed items retryable from the UI.
- [x] **VII. Security** — owner login (argon2, server sessions, CSRF header); write-only
      secrets; email tokens hashed, single-use, expiring, GET-confirm-POST; webhook secret.
- [x] **VIII. Test-first** — adapters with fakes for Radarr, TMDB, Ollama, Seerr, SMTP;
      tests listed per story in tasks; ruff, mypy strict, Biome in CI.
- [x] **IX. UX & accessibility** — mobile-first layout (bottom tabs ↔ sidebar), EN/FR via
      react-intl, Radix primitives, axe checks at two widths, explicit empty/error states.
- [x] **X. Observability** — JSON logs with `radarr_id`/`decision_id` context; searchable
      history; status page.
- [x] **XI. Simplicity** — one image, SQLite, in-process worker; dependencies limited to the
      list above, each tied to a requirement (aiosmtplib → FR-018, argon2 → FR-028,
      openapi-typescript → typed client, react-intl → FR-024).

## Project Structure

### Documentation (this feature)

```text
specs/001-movie-triage-mvp/
├── plan.md              # This file
├── research.md          # Phase 0: API findings and decisions
├── data-model.md        # Phase 1: entities, state machine, validation
├── quickstart.md        # Phase 1: end-to-end validation against a test Radarr
├── contracts/
│   ├── http-api.md          # Triage's own API, webhook, email links
│   └── external-services.md # Allowed calls to Radarr, TMDB, Ollama, Seerr, SMTP
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml            # uv project, ruff, mypy, pytest config
├── alembic.ini
├── migrations/versions/
├── src/triage/
│   ├── app/                  # FastAPI app factory, lifespan, static files, CLI (serve, migrate)
│   ├── api/                  # routers: setup/auth, settings, categories, decisions, scans,
│   │                         #          status, webhooks, review links
│   ├── core/                 # settings model, db session, security (sessions, CSRF, tokens),
│   │                         #   logging (JSON), errors
│   ├── domain/               # categories & rules, scoring engine, decision state machine,
│   │                         #   presets
│   ├── adapters/             # radarr, tmdb, ollama, seerr, smtp (+ fakes in tests)
│   ├── worker/               # poller, work queue, scan runner, email batcher
│   └── models/               # SQLAlchemy models
└── tests/
    ├── unit/                 # scoring, state machine, presets, token handling
    ├── integration/          # API + worker with fake adapters, SQLite in tmp
    └── contract/             # adapters vs recorded payloads (Radarr 6, TMDB, Ollama, Seerr)

frontend/
├── package.json · vite.config.ts · biome.json · playwright.config.ts
├── src/
│   ├── api/                  # generated types + fetch client + TanStack Query hooks
│   ├── shell/                # layout (sidebar / bottom tabs), auth guard, theme
│   ├── design-system/        # tokens (CSS variables), Radix-based components
│   ├── i18n/                 # en.json, fr.json, react-intl setup
│   └── features/             # dashboard, review, decisions, categories, scans, settings,
│                             #   status, setup/login, link-confirmation
└── tests/{unit,e2e}/

deploy/
├── Dockerfile                # node:22-alpine → python:3.12-slim, PUID/PGID entrypoint
├── entrypoint.sh
├── docker-compose.yml
└── DOCKERHUB.md

.gitlab-ci.yml                # validate · test · build · publish (tags)
GITHUB_RELEASES.md · README.md · CHANGELOG.md
```

**Structure Decision**: web application with `backend/` and `frontend/` (Portalab layout,
minus modules/plugins/connectors), plus `deploy/` for the single image. The backend serves the
built frontend, so one container and one port (9393) serve everything.

## Complexity Tracking

| Item | Why | Simpler alternative rejected because |
|---|---|---|
| Spec FR-022g clarified: Seerr requests are verified, not edited | Seerr returns 409 for non-pending requests and re-sends requests to Radarr on every update (research R6) | Editing requests is impossible for approved ones and risky for pending ones; verification keeps the user's goal (requests not broken) |
| Persistent `work_item` table instead of plain asyncio tasks | Restart safety and visible retries (V, VI) | In-memory tasks lose pending moves/emails on restart |
| Generated TypeScript client (`openapi-typescript`) | Same as Portalab; prevents API drift | Hand-written types drift silently |
