# Tasks: Triage MVP — sort newly requested movies into the right library

**Input**: Design documents from `/specs/001-movie-triage-mvp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: required (Constitution VIII). Within each story, tests are written first and must
fail before the implementation tasks of that story start. Every external service is replaced
by its fake from T019–T023.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: user story from spec.md (US1–US9)
- Paths are relative to the repository root (`backend/`, `frontend/`, `deploy/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: project skeletons and tooling, mirroring Portalab's configuration scaled down.

- [X] T001 Create the backend uv project in backend/pyproject.toml (package `triage` under backend/src/triage, Python 3.12, dependencies from plan.md, dev deps pytest, pytest-asyncio, ruff, mypy, httpx test client; console script `triage = triage.app.cli:main`) and run `uv lock`
- [X] T002 [P] Configure ruff (line length 110, rules E F W I B UP S ASYNC RUF SIM PTH DTZ as in Portalab), mypy strict and pytest (asyncio_mode=auto, testpaths) in backend/pyproject.toml
- [X] T003 [P] Create the frontend Vite 7 + React 19 + TypeScript 5.9 project in frontend/ (package.json scripts dev, build, lint, typecheck, test, gen:api, check:api-drift; tsconfig.json; vite.config.ts proxying /api to http://127.0.0.1:9393)
- [X] T004 [P] Add Biome config frontend/biome.json (recommended + a11y, 2 spaces, width 110) and Tailwind 4 setup in frontend/src/styles.css
- [X] T005 [P] Add Vitest + Testing Library config in frontend/vite.config.ts and Playwright + @axe-core/playwright config with 360 px and 1280 px projects in frontend/playwright.config.ts
- [X] T006 [P] Create .gitignore, .editorconfig and README.md skeleton (English: what Triage does, quick start placeholder) at the repository root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: database, security, logging, adapters with fakes, scoring engine, worker
skeleton, frontend shell. No user story can start before this phase is complete.

### Core backend

- [X] T007 Implement JSON structured logging with context vars (`radarr_id`, `decision_id`, `work_item_id`) in backend/src/triage/core/logging.py
- [X] T008 Implement the async SQLite engine (WAL, foreign keys on), session factory and FastAPI dependency in backend/src/triage/core/db.py
- [X] T009 Create SQLAlchemy models for owner, session, setting, category, rule, movie_ref, metadata_cache, arrival, decision, review_link, scan, work_item, audit_event per data-model.md in backend/src/triage/models/ (one file per concept)
- [X] T010 Configure Alembic (backend/alembic.ini, backend/migrations/env.py) and generate the initial migration backend/migrations/versions/0001_initial.py
- [X] T011 Implement the typed settings model (Pydantic) with secret fields write-only and `{set: bool}` serialization, loaded from the `setting` table, in backend/src/triage/core/settings.py
- [X] T012 [P] Implement the error envelope and exception handlers in backend/src/triage/core/errors.py
- [X] T013 Implement owner password hashing (argon2id), server-side sessions (hashed ids, sliding 30 days), CSRF header check, login rate limiter, and the `require_owner` dependency in backend/src/triage/core/security.py
- [X] T014 Implement the app factory (lifespan starting/stopping the worker, routers, static files from `static/` with SPA fallback, `/healthz`) and the CLI `serve` / `migrate` in backend/src/triage/app/main.py and backend/src/triage/app/cli.py
- [X] T015 [P] Write unit tests for security (hashing, session expiry, CSRF rejection, rate limit) in backend/tests/unit/test_security.py
- [X] T016 Implement setup and auth endpoints (`/setup/status`, `/setup`, `/auth/login`, `/auth/logout`, `/auth/me`) per contracts/http-api.md in backend/src/triage/api/auth.py
- [X] T017 [P] Write integration tests for setup/login/logout, setup refused once an owner exists, and 401 on protected routes in backend/tests/integration/test_auth.py

### Adapters and fakes (contracts/external-services.md)

- [X] T018 Create the shared test fixtures (temp SQLite, app client logged in as owner, fake adapters injected) in backend/tests/conftest.py
- [X] T019 [P] Implement the Radarr adapter (system status, root folders, movies, movie by id, editor move with deleteFiles/addImportExclusion forced false) in backend/src/triage/adapters/radarr.py and its in-memory fake in backend/tests/fakes/radarr.py
- [X] T020 [P] Implement the TMDB adapter (configuration test, movie details with keywords and release_dates, ≤ 4 req/s limiter, 7-day cache in metadata_cache) in backend/src/triage/adapters/tmdb.py and its fake in backend/tests/fakes/tmdb.py
- [X] T021 [P] Implement the Ollama adapter (`/api/tags`, `/api/chat` with JSON-schema `format`, temperature 0, timeout, answer validation) in backend/src/triage/adapters/ollama.py and its fake (scripted answers, timeouts, invalid JSON) in backend/tests/fakes/ollama.py
- [X] T022 [P] Implement the Seerr adapter (status, paginated request lookup by tmdbId; no write calls) in backend/src/triage/adapters/seerr.py and its fake in backend/tests/fakes/seerr.py
- [X] T023 [P] Implement the SMTP adapter (aiosmtplib, STARTTLS/SSL, multipart HTML + text) in backend/src/triage/adapters/smtp.py and its fake (captured messages, failure mode) in backend/tests/fakes/smtp.py
- [X] T024 [P] Write contract tests for each adapter against recorded payloads (Radarr 6.2 movie and rootfolder, TMDB movie with append_to_response, Ollama chat, Seerr request page) in backend/tests/contract/ (fixtures in backend/tests/contract/payloads/)

### Domain core

- [X] T025 Implement signal extraction (normalize Radarr fields + TMDB enrichment into facts: genres, keywords, companies, certifications, original language) in backend/src/triage/domain/signals.py
- [X] T026 Implement the scoring engine (rule matching with is/contains/is_not, case- and accent-insensitive; weights; decisive rules; fallback base score; confidence = top/(top+second+k); AI signal weight; move test with threshold and margin) per research R5 in backend/src/triage/domain/scoring.py
- [X] T027 [P] Write unit tests for the scoring engine (decisive wins, two decisive → hold, fallback, close scores → hold, single weak signal stays below 0.8, AI contribution, AI ignored when decisive) in backend/tests/unit/test_scoring.py
- [X] T028 Implement the decision state machine (transitions and guards from data-model.md, link revocation on leaving held/proposed, superseded on arrival close) in backend/src/triage/domain/decisions.py
- [X] T029 [P] Write unit tests for every allowed and forbidden transition in backend/tests/unit/test_decision_states.py
- [X] T030 Implement the persistent work queue (enqueue, claim one, exponential backoff 1 min → 1 h, max 8 attempts, failed state) and the worker loop started by the lifespan in backend/src/triage/worker/queue.py and backend/src/triage/worker/runner.py
- [X] T031 [P] Write unit tests for the work queue (backoff schedule, max attempts, restart resumes pending items) in backend/tests/unit/test_queue.py
- [X] T032 Implement the audit log writer (append-only) in backend/src/triage/domain/audit.py

### Frontend shell

- [X] T033 Generate the OpenAPI schema from the backend (`triage openapi -o backend/openapi.json`) and the typed client with openapi-typescript into frontend/src/api/generated/; add the fetch wrapper (cookie, CSRF header, error envelope) in frontend/src/api/client.ts
- [X] T034 [P] Create design tokens (CSS variables, light/dark, focus rings, reduced motion) and base components (Button, Card, Badge, Dialog, Select, Switch, Input, EmptyState, ErrorState, Skeleton) on Radix in frontend/src/design-system/
- [X] T035 [P] Set up react-intl with frontend/src/i18n/en.json and frontend/src/i18n/fr.json, locale from the owner profile or browser, and a language switch in frontend/src/i18n/index.tsx
- [X] T036 Implement the app shell (sidebar on desktop, bottom tab bar on mobile, theme toggle, auth guard redirecting to setup/login) and routes in frontend/src/shell/
- [X] T037 Implement the setup and login screens in frontend/src/features/auth/
- [ ] T038 [P] Write Playwright tests for setup → login → logout at 360 px and 1280 px with axe checks in frontend/tests/e2e/auth.spec.ts

**Checkpoint**: an owner can sign in to an empty shell; adapters, scoring, and queue are tested.

---

## Phase 3: User Story 3 — I define my own categories and rules (Priority: P1)

**Goal**: categories with rules, fallback, preset, history-safe edits. Done first among the P1
stories because every other story classifies against categories.

**Independent Test**: create a category with rules and a library, then classify a matching
movie with the simulation endpoint (or a unit-level call) and get that category.

### Tests for User Story 3

- [X] T039 [P] [US3] Write integration tests for category CRUD, validation (root folder must exist in Radarr fake and not be an intake folder, single fallback, cannot delete the last category), reorder, version increments in backend/tests/integration/test_categories.py
- [X] T040 [P] [US3] Write integration tests for presets (list, apply movies-animation → two categories with rules, root folders unset until chosen) in backend/tests/integration/test_presets.py

### Implementation for User Story 3

- [X] T041 [US3] Implement the movies-animation preset (Animation genre decisive-weight 60, keywords anime/stop-motion/cartoon/animated feature 30, studios Pixar, Walt Disney Animation Studios, DreamWorks Animation, Studio Ghibli, Illumination, Blue Sky, Aardman, Laika, Sony Pictures Animation, Toei Animation 40; fallback "Films") in backend/src/triage/domain/presets.py
- [X] T042 [US3] Implement the categories and presets endpoints per contracts/http-api.md in backend/src/triage/api/categories.py
- [X] T043 [P] [US3] Implement the categories list and editor (name, library picker from `/radarr/root-folders`, description, fallback switch, rule rows with field/operator/value/weight/decisive, reorder, delete confirm) in frontend/src/features/categories/
- [X] T044 [P] [US3] Implement the first-run preset card (apply preset, then pick libraries) in frontend/src/features/categories/PresetCard.tsx
- [ ] T045 [US3] Add category strings in frontend/src/i18n/en.json and frontend/src/i18n/fr.json and a Playwright test for creating a category on mobile in frontend/tests/e2e/categories.spec.ts

**Checkpoint**: categories are editable and the preset works.

---

## Phase 4: User Story 1 — Confident movies are sorted without me (Priority: P1) 🎯 MVP core

**Goal**: poll intake folders, classify, move confident movies in automatic mode,
idempotently.

**Independent Test**: with the Radarr fake holding an animated and a live-action movie in the
intake folder and automatic mode on, one poll moves each to its library exactly once.

### Tests for User Story 1

- [X] T046 [P] [US1] Write integration tests for the poller (new movie → arrival + classify item; repeated polls and restart → no duplicate arrival; movie outside intake ignored; movie leaving intake → arrival closed, pending work superseded) in backend/tests/integration/test_poller.py
- [X] T047 [P] [US1] Write integration tests for the classify→move pipeline (Toy Story-like → animation library, Heat-like → fallback, move confirmed by re-reading Radarr, editor body never contains deleteFiles=true, Radarr down → retried, no move) in backend/tests/integration/test_pipeline_auto.py
- [X] T048 [P] [US1] Write integration tests for the AI path (rules inconclusive → AI called with category descriptions; AI timeout/invalid answer → rules only or hold; AI never called when a decisive rule matched) in backend/tests/integration/test_ai_path.py

### Implementation for User Story 1

- [X] T049 [US1] Implement the poller (interval from settings, wake-up event, arrival open/close per research R10, movie_ref refresh) in backend/src/triage/worker/poller.py
- [X] T050 [US1] Implement the classify job (gather signals with TMDB cache, score, consult AI when inconclusive, store decision with signals/ai/scores/snapshot, route to move/hold/proposal by mode) in backend/src/triage/worker/classify.py
- [X] T051 [US1] Implement the AI prompt builder (system prompt, category list with keys and descriptions, movie facts) and verdict mapping in backend/src/triage/domain/ai_prompt.py
- [X] T052 [US1] Implement the move job (editor call, confirmation read, decision → moved, arrival closed, audit event; failure → retry/failed) in backend/src/triage/worker/move.py
- [X] T053 [US1] Implement `/dashboard`, `/decisions` (filters, cursor pagination) and `/decisions/{id}` in backend/src/triage/api/decisions.py
- [X] T054 [P] [US1] Implement the dashboard (counts, mode badge, latest decisions with poster, category, confidence, outcome; empty state explaining what will appear) in frontend/src/features/dashboard/
- [X] T055 [P] [US1] Implement the decision detail view (signals table labelled "metadata", AI block labelled "AI interpretation" with reasoning, per-category scores bar, snapshot version, audit trail) in frontend/src/features/decisions/DecisionDetail.tsx
- [ ] T056 [US1] Add dashboard/decision strings (EN/FR) and a Playwright test of dashboard + decision detail with axe at both widths in frontend/tests/e2e/dashboard.spec.ts

**Checkpoint**: Triage sorts confident movies on its own and explains each decision.

---

## Phase 5: User Story 2 — Doubtful movies wait for me, decided in one tap (Priority: P1)

**Goal**: hold, review queue, batched email with single-use links.

**Independent Test**: a conflicting-signals movie stays in intake, appears in Review, produces
one email; choosing from the link or the queue moves it; the link then answers "already
decided".

### Tests for User Story 2

- [X] T057 [P] [US2] Write integration tests for holding (below threshold or close second → held, never moved; one email per poll run grouping held movies; SMTP failure → retried, review item still visible) in backend/tests/integration/test_hold_and_email.py
- [X] T058 [P] [US2] Write integration tests for review links (GET shows confirmation and never acts; POST moves and marks used; second use and expired → 410; decided in UI → links revoked; "leave in intake" → left_in_intake, never proposed again for that arrival) in backend/tests/integration/test_review_links.py

### Implementation for User Story 2

- [X] T059 [US2] Implement review-link tokens (32 random bytes, SHA-256 storage, expiry, single use, revocation) in backend/src/triage/core/tokens.py
- [X] T060 [US2] Implement the email batcher job and templates (HTML + text, poster, reasons, one link per category + leave in intake, EN/FR by owner locale) in backend/src/triage/worker/email.py and backend/src/triage/templates/
- [X] T061 [US2] Implement `/review`, `/decisions/{id}/apply` and the public `/r/{token}` GET (confirmation page) and POST in backend/src/triage/api/review.py
- [X] T062 [P] [US2] Implement the review queue (cards with poster, reasons, one button per category, leave in intake; optimistic update; empty state "nothing to review") in frontend/src/features/review/
- [ ] T063 [US2] Add review strings (EN/FR) and a Playwright test deciding a held movie in one tap on mobile in frontend/tests/e2e/review.spec.ts

**Checkpoint**: doubt never moves a movie, and the owner settles it in one tap.

---

## Phase 6: User Story 4 — Preview what Triage would do (Priority: P1)

**Goal**: preview mode (default), apply/dismiss/apply-confident, simulate one movie.

**Independent Test**: in preview mode, arrivals produce proposals and nothing moves; applying
one moves only that one; simulate never moves.

### Tests for User Story 4

- [X] T064 [P] [US4] Write integration tests for preview mode (default mode, proposals only, apply one, apply confident, pick another category, dismiss, switching to automatic leaves pending proposals untouched) in backend/tests/integration/test_preview.py
- [X] T065 [P] [US4] Write integration tests for simulate (returns a decision with status simulated, no move, no review link, no email) in backend/tests/integration/test_simulate.py

### Implementation for User Story 4

- [X] T066 [US4] Implement `/decisions/{id}/dismiss`, `/decisions/apply-confident` and `/movies/{radarr_id}/simulate` in backend/src/triage/api/decisions.py
- [X] T067 [P] [US4] Add proposals to the review screen (tab "Proposals", apply / change category / dismiss, "Apply all confident" with count confirmation) in frontend/src/features/review/Proposals.tsx
- [X] T068 [P] [US4] Add the mode switch with explanation (Preview ↔ Automatic, confirmation when enabling automatic) in frontend/src/features/settings/ModeSwitch.tsx and a "Simulate" action on movie rows in frontend/src/features/decisions/SimulateButton.tsx
- [ ] T069 [US4] Add preview strings (EN/FR) and a Playwright test applying a proposal in frontend/tests/e2e/preview.spec.ts

**Checkpoint**: the owner can check Triage's judgement before letting it act.

---

## Phase 7: User Story 5 — Scan movies already in a folder (Priority: P1)

**Goal**: owner-started scans of any root folder producing proposals, with progress and cancel.

**Independent Test**: scanning a library holding a misplaced animated movie proposes moving
it, moves nothing alone, and moves it when applied.

### Tests for User Story 5

- [X] T070 [P] [US5] Write integration tests for scans (start returns 202; one running at a time → 409; proposals with in_place flag; progress; cancel keeps partial results; corrected movies still proposed; apply-confident limited to the scan and to movies not in place) in backend/tests/integration/test_scans.py

### Implementation for User Story 5

- [X] T071 [US5] Implement the scan runner (enumerate movies of the folder from Radarr, enqueue scan_movie items, classify as proposals, progress counters, cancellation) in backend/src/triage/worker/scan.py
- [X] T072 [US5] Implement `/scans`, `/scans/{id}`, `/scans/{id}/results`, `/scans/{id}/cancel` in backend/src/triage/api/scans.py
- [X] T073 [P] [US5] Implement the scans screen (folder picker, start, live progress, results grouped "to move" / "in place" / "doubtful", apply one, apply all confident, cancel) in frontend/src/features/scans/
- [ ] T074 [US5] Add scan strings (EN/FR) and a Playwright test running a scan and applying results in frontend/tests/e2e/scans.spec.ts

**Checkpoint**: the existing backlog and past mistakes can be cleaned up safely.

---

## Phase 8: User Story 6 — Requests keep working after a move (Priority: P1)

**Goal**: same Radarr entry always; Seerr tracking verified and shown; folder warnings.

**Independent Test**: after a move, the decision shows the requester and "request tracked";
no Seerr write call was made; a category library reported inaccessible appears on the status
page.

### Tests for User Story 6

- [X] T075 [P] [US6] Write integration tests for request verification (verify_request item after move; tracked when Seerr fake still resolves tmdbId → same request; Seerr down → retried, move kept; the Seerr fake records zero write calls; the Radarr fake records zero delete/add calls) in backend/tests/integration/test_requests.py

### Implementation for User Story 6

- [X] T076 [US6] Implement the verify_request job and decision.request_check update in backend/src/triage/worker/verify_request.py
- [X] T077 [US6] Add category-library checks (missing or not accessible in Radarr) to the status computation in backend/src/triage/domain/health.py
- [X] T078 [P] [US6] Show requester and request status on decision cards and detail in frontend/src/features/decisions/RequestBadge.tsx

**Checkpoint**: Seerr requests demonstrably keep tracking moved movies.

---

## Phase 9: User Story 7 — See, undo, and correct what Triage did (Priority: P2)

**Goal**: history with search/filters, corrections, never re-sort corrected movies.

**Independent Test**: correct an automatic move from its decision; the movie changes library,
history shows both, later polls never auto-sort it.

### Tests for User Story 7

- [X] T079 [P] [US7] Write integration tests for corrections (to another category, back to intake → corrected flag, new arrival never auto-sorted, history keeps both decisions and audit events) and history filters in backend/tests/integration/test_corrections.py

### Implementation for User Story 7

- [X] T080 [US7] Implement `/decisions/{id}/correct` and the corrected-movie guard in the classify job in backend/src/triage/api/decisions.py and backend/src/triage/worker/classify.py
- [X] T081 [P] [US7] Implement the history screen (search, filters by outcome/category/source/date, infinite list, correct action with category picker) in frontend/src/features/decisions/History.tsx
- [ ] T082 [US7] Add history strings (EN/FR) and a Playwright test correcting a move in frontend/tests/e2e/history.spec.ts

---

## Phase 10: User Story 8 — Configure connections and see their health (Priority: P2)

**Goal**: settings with tests, write-only secrets, status page, retry failed items.

**Independent Test**: enter connection details, run each test, see a reachable and an
unreachable service on the status page; secrets never come back in responses.

### Tests for User Story 8

- [X] T083 [P] [US8] Write integration tests for settings (PATCH validation incl. intake folders existing in Radarr; secrets write-only and never serialized; test endpoints with unsaved values; `/ollama/models`, `/radarr/root-folders`) in backend/tests/integration/test_settings.py
- [X] T084 [P] [US8] Write integration tests for `/status` (per-service states ok/degraded/down/disabled, last/next poll, queue counts, failed items) and `/work-items/{id}/retry`, `/poll` in backend/tests/integration/test_status.py

### Implementation for User Story 8

- [X] T085 [US8] Implement `/settings`, `/settings/test/{service}`, `/radarr/root-folders`, `/ollama/models` in backend/src/triage/api/settings.py
- [X] T086 [US8] Implement health probes (cached 60 s) and `/status`, `/poll`, `/work-items/{id}/retry` in backend/src/triage/api/status.py and backend/src/triage/domain/health.py
- [X] T087 [P] [US8] Implement the settings screens (sections Radarr + intake folders, TMDB, AI, Seerr + webhook URL/secret to copy, Email, Sorting thresholds; Test buttons with results; secret fields showing "set") in frontend/src/features/settings/
- [X] T088 [P] [US8] Implement the status page (service cards, queue, failed items with retry, folder warnings) in frontend/src/features/status/
- [ ] T089 [US8] Add settings/status strings (EN/FR) and Playwright tests for settings on mobile and the status page in frontend/tests/e2e/settings.spec.ts

---

## Phase 11: User Story 9 — Requests reach Triage immediately (Priority: P3)

**Goal**: secret-protected Seerr webhook triggering an immediate poll.

**Independent Test**: an approved-request webhook triggers a poll within seconds; a wrong
secret gets 401 and no poll.

- [X] T090 [P] [US9] Write integration tests for the webhook (MEDIA_APPROVED and MEDIA_AUTO_APPROVED movie → 202 + poll wake-up; TEST_NOTIFICATION → 204; tv or other types ignored; wrong/missing secret → 401) in backend/tests/integration/test_webhook.py
- [X] T091 [US9] Implement `POST /api/v1/webhooks/seerr` in backend/src/triage/api/webhooks.py

---

## Phase 12: Polish & Cross-Cutting Concerns

- [ ] T092 [P] Write deploy/Dockerfile (node:22-alpine frontend build → python:3.12-slim, uv sync --frozen --no-dev, static files, `/config` volume, port 9393, healthcheck on /healthz) and deploy/entrypoint.sh (PUID/PGID/UMASK like Pressarr v0.2.0, runs migrations then serve)
- [ ] T093 [P] Write deploy/docker-compose.yml and deploy/DOCKERHUB.md (English)
- [ ] T094 [P] Write .gitlab-ci.yml (validate: ruff, mypy, Biome, typecheck, openapi drift; test: pytest, vitest; build: image; publish: Docker Hub on tags; release notes from GITHUB_RELEASES.md) following Portalab's pipeline
- [ ] T095 [P] Add accessibility pass: keyboard navigation of review and editor, reduced motion, contrast in both themes; axe on every e2e spec in frontend/tests/e2e/
- [ ] T096 [P] Write README.md (English: features, screenshots placeholder, quick start, Radarr/Seerr/Ollama setup, how scoring works, safety guarantees) and GITHUB_RELEASES.md with a `# v0.1.0` block
- [ ] T097 Run quickstart.md end to end against the test Radarr (classifarr-test-radarr) and fix what fails
- [ ] T098 Verify all quality gates (ruff, mypy strict, Biome, pytest, vitest, Playwright + axe) and the Docker image build, then clean the test image and build cache

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (1)** → **Foundational (2)** → user stories.
- **US3 (Phase 3)** first: every story classifies against categories.
- **US1 (Phase 4)** depends on US3; **US2, US4, US5** depend on US1's classify job (T050)
  and can then proceed in parallel.
- **US6** depends on US1's move job (T052).
- **US7** depends on US1; **US8** only on Foundational (its UI can start early);
  **US9** depends on US1's poller (T049).
- **Polish (12)** after the stories planned for the release.

### Within each story

Tests first (they must fail), then backend jobs/endpoints, then frontend, then strings and
e2e test.

### Parallel opportunities

- Setup: T002–T006 together after T001.
- Foundational: adapters T019–T023 together; T027, T029, T031 together; frontend T034, T035
  alongside backend work.
- After US1: US2, US4, US5 in parallel; US8 UI at any time after Foundational.

### Parallel example: User Story 1

```text
Together: T046 test_poller.py · T047 test_pipeline_auto.py · T048 test_ai_path.py
Then:     T049 poller → T050 classify (+T051 prompt) → T052 move → T053 API
Together: T054 dashboard · T055 decision detail
```

## Implementation Strategy

### MVP first

1. Phases 1–2 (setup, foundations).
2. Phase 3 (US3 categories) + Phase 4 (US1 automatic sorting) + Phase 6 (US4 preview, the
   default mode) → usable: the owner applies the preset, previews, then turns automatic on.
3. Phase 5 (US2 review + email) → doubtful movies handled.
4. **Stop and validate** with quickstart.md steps 3–5.

### Incremental delivery

5. US5 scans → backlog cleanup.
6. US6 request verification → Seerr confidence.
7. US8 settings UI and status (minimal settings already needed by step 2: implement T085
   early if no settings UI exists yet), US7 history and corrections, US9 webhook.
8. Polish → first release v0.1.0.
