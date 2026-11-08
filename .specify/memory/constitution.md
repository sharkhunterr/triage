<!--
SYNC IMPACT REPORT
==================
Version change: (unfilled template) → 1.0.0
Bump rationale: Initial ratification. The previous file was the unpopulated Spec Kit
template (all [PLACEHOLDER] tokens). This is the first concrete constitution for Triage,
so it is adopted at 1.0.0.

Principles (all added — 11 total):
  I.    Human Authority & Safe Automation
  II.   Configurable Categories
  III.  Explainable Decisions
  IV.   Rules First, AI Second
  V.    Source of Truth
  VI.   Resilience & Degraded Mode
  VII.  Security
  VIII. Test-First & Quality
  IX.   UX & Accessibility
  X.    Observability
  XI.   Simplicity

Added sections: Core Principles (I–XI); Technology Constraints; Development Workflow;
Governance.
Removed sections: None (template placeholders replaced).

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gates made concrete.
  ✅ .specify/templates/spec-template.md — reviewed; its mandatory sections (user stories,
     functional requirements, success criteria, edge cases) already fit; no change required.
  ✅ .specify/templates/tasks-template.md — reviewed; test-first ordering and polish phase
     cover principles VIII and X; no structural change required.
  ✅ CLAUDE.md (project root) — reviewed; Git and language rules match the Development
     Workflow section.

Deferred items / TODOs: None.
-->

# Triage Constitution

Triage is a self-hosted service that sorts newly requested movies into the right Radarr
library. Requests made by non-admin users in Overseerr/Jellyseerr land in an *intake* root
folder (for example `Nouveaux/Non Triés`); Triage reads each new movie's metadata, applies
the user's own categories (for example *Films* and *Dessins Animés*), asks a local AI when
the metadata alone is not conclusive, and either moves the movie to the matching root folder
or holds it in the intake folder and notifies the user.

This Constitution defines the non-negotiable principles that every specification, plan,
task, and implementation MUST obey. It governs **how** Triage is built; **what** it does is
defined by the feature specifications under `specs/`.

## Core Principles

### I. Human Authority & Safe Automation

Triage automates the obvious and leaves the doubtful to a human.

- A movie MUST NOT be moved unless the decision reaches the configured confidence threshold.
- A movie below the threshold MUST stay in the intake folder, be marked as awaiting review,
  and the user MUST be notified.
- Triage MUST NEVER delete media files, remove a movie from Radarr, or change anything other
  than a movie's root folder (and the file move Radarr performs for it).
- Every move MUST be traceable and MUST be reversible from the interface (move back, or move
  to another category).
- A manual decision by the user MUST always take precedence over an automatic one.

*Rationale: a wrong move is worse than no move — the user then has to notice it and fix it
by hand, which is exactly the chore Triage exists to remove.*

### II. Configurable Categories

Triage MUST NOT hard-code any taxonomy.

- Categories (name, Radarr root folder, description for the AI, metadata rules) MUST be user
  configuration, editable from the interface.
- The intake folder(s) to watch MUST be configurable.
- "Films vs. animation" MUST ship only as an optional preset; any other split (documentaries,
  kids, concerts, languages…) MUST be expressible without code changes.
- Changing a category MUST NOT rewrite past decisions: history keeps the category definition
  in force when the decision was made.

*Rationale: the user's need is animation today and something else tomorrow; a generic rule
engine is the product, the animation split is one configuration of it.*

### III. Explainable Decisions

Every decision MUST be understandable without reading logs.

- A decision MUST record: the signals observed (genres, keywords, companies, certification,
  language…), the weight each contributed, the AI verdict and its stated reasoning when the
  AI was consulted, the final confidence, and the outcome (moved, held, overridden).
- The interface and the doubt notification MUST show why a movie was held, so the user can
  decide in one look.
- Facts from metadata and inferences from the AI MUST be distinguishable in what is shown.

*Rationale: the user only trusts automation they can check; a held movie with no reason is a
dead end.*

### IV. Rules First, AI Second

Deterministic rules decide; the AI helps where rules are not conclusive.

- Metadata rules MUST be evaluated first and MUST give the same result for the same inputs.
- The local AI (Ollama) MAY arbitrate between categories or add a weighted signal; it MUST
  NOT override a rule configured as decisive.
- When the AI is disabled, unavailable, too slow, or returns an unusable answer, Triage MUST
  fall back to the rules alone; if they are not conclusive, the movie MUST be held — never
  moved on a guess, never left blocking the queue.
- No cloud AI MAY be called unless the user explicitly configures one.

*Rationale: rules are predictable and testable; the AI is valuable for the ambiguous cases
(adult animation, live action mixed with animation) but must never become a single point of
failure or a source of silent wrong moves.*

### V. Source of Truth

- Radarr owns movies, files, and root folders; TMDB owns metadata.
- Triage MUST store only its own settings, decisions, history, and pending reviews.
- Processing MUST be idempotent and restart-safe: re-reading the same movie MUST NOT produce
  a second move or a duplicate notification.
- A movie that is no longer in an intake folder (moved by a human or another tool) MUST be
  left untouched.

*Rationale: Radarr is the system of record; Triage is a decision layer on top of it and must
never fight a human or another tool over where a movie lives.*

### VI. Resilience & Degraded Mode

- An outage or slow response of Radarr, TMDB, Ollama, or the mail server MUST NOT cause a
  wrong move.
- Failed operations MUST be retried with backoff, and permanently failing items MUST surface
  in the interface instead of being dropped.
- The health of each dependency MUST be visible in the interface, distinct from the state of
  the work queue.

*Rationale: a home lab has services that restart; the queue must pick up where it left off.*

### VII. Security

- The interface MUST require authentication, even on a LAN.
- Secrets (Radarr API key, TMDB key, SMTP password, signing key) MUST stay server-side and
  MUST NEVER be sent to the browser; settings screens show whether a secret is set, not its
  value.
- One-click decision links in emails MUST be signed, single-use, and expiring.
- Every action that moves a movie MUST be authorized server-side.

*Rationale: Triage holds an API key able to move a whole library; it must not leak it or let
an unauthenticated request use it.*

### VIII. Test-First & Quality

- Acceptance criteria MUST be verifiable by automated tests; a criterion that cannot be
  tested is incomplete and MUST be revised before implementation.
- Every external service (Radarr, TMDB, Ollama, SMTP, Overseerr) MUST sit behind an adapter
  with a fake used in tests; no test MAY depend on a live external service.
- Tests MUST cover nominal decisions, ambiguity, dependency outages, idempotency, and
  authorization.
- Code MUST pass ruff, mypy (strict) and Biome before it is merged.

*Rationale: Triage moves real libraries; its decision engine and its failure paths must be
proven before they run on a user's media.*

### IX. UX & Accessibility

- The interface MUST be modern and simple, and MUST be equally complete on a smartphone and
  on a desktop — mobile is not a reduced subset.
- The interface MUST be available in English and French.
- It MUST be usable with keyboard and touch, honor reduced motion, and keep sufficient
  contrast in light and dark themes.
- No state MAY be a dead end: an empty list explains what will appear there, an error says
  what to do next.

*Rationale: reviewing a held movie is a ten-second task done from a phone; anything harder
defeats the purpose.*

### X. Observability

- Logs MUST be structured (JSON) and correlate each line with the movie being processed.
- Decision history MUST be kept and searchable in the interface.
- A status page MUST show dependency health, queue state, and the last processing run.

*Rationale: when a movie lands in the wrong place, the user must find out why in the
interface, not in a container's log.*

### XI. Simplicity

- Triage MUST ship as a single Docker image with SQLite storage; no external database,
  message queue, or cache MAY be required.
- A technology, abstraction, or dependency MUST NOT be added unless a requirement needs it.
- Each concern MUST have one implementation; parallel mechanisms MUST NOT be introduced.

*Rationale: Triage does one job for one household; its footprint and its maintenance must
stay proportional to that.*

## Technology Constraints

Aligned with Portalab's stack, scaled down to a single-service app.

- **Backend**: Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2 (async) with aiosqlite,
  Alembic migrations, httpx for every outbound call, uv for dependencies, ruff and mypy
  (strict).
- **Frontend**: TypeScript 5.9, React 19, Vite 7, TanStack Query, React Router, Radix UI and
  Tailwind 4 on CSS-variable design tokens, lucide-react icons, Biome; Vitest for unit tests,
  Playwright with axe for end-to-end and accessibility checks.
- **Integrations**: Radarr API v3 (root folders, movie editor), TMDB API v3, Ollama HTTP API,
  SMTP for email; Overseerr/Jellyseerr is optional (webhook) — Radarr remains the source of
  what is in the intake folder.
- **Delivery**: one Docker image serving the API and the built frontend, running as
  `PUID`/`PGID`; GitLab CI with validate, test, build, and publish stages; images published
  to Docker Hub.
- Deviations from this stack MUST be justified in the plan's Complexity Tracking section.

## Development Workflow

- Bugs, features, and ideas are tracked as issues on the local GitLab
  (http://192.168.1.60/root/triage); work references its issue.
- Commits follow Conventional Commits and use the repository owner's Git identity.
- Commits, merge requests, and code MUST NOT contain a "Co-Authored-By" line or any mention
  of Claude, Claude Code, or Anthropic.
- Nothing is pushed, force-pushed, tagged, or released without an explicit request.
- README, release notes, and the Docker Hub page are written in English; each release adds a
  `# vX.Y.Z` block at the top of `GITHUB_RELEASES.md`.
- Features follow the Spec Kit flow: specify → clarify → plan → tasks → implement, each on
  its own numbered branch.

## Governance

This Constitution is the authoritative reference for Triage's development principles. It
governs specifications, plans, tasks, and implementations.

**Authority and precedence.**
- Specifications MUST comply with this Constitution.
- Plans MUST check their design against every principle in the Constitution Check gate and
  MUST record any deviation, with its justification, in Complexity Tracking.
- Implementations MUST comply with their specification and this Constitution.

**Amendment procedure.**
- Any change to a principle MUST be documented, versioned, and reflected in the Sync Impact
  Report at the top of this file.
- Amendments MUST be propagated to the dependent templates (`plan-template.md`,
  `spec-template.md`, `tasks-template.md`) and to `CLAUDE.md` when they affect them.

**Versioning policy (semantic).**
- MAJOR: a principle is removed or redefined in a backward-incompatible way.
- MINOR: a principle or section is added, or guidance is materially expanded.
- PATCH: clarifications, wording, or non-semantic refinements.

**Compliance review.**
- Every specification and plan review MUST verify compliance with the applicable principles.
- Complexity or deviation MUST be justified in writing, or the change MUST be simplified.

**Version**: 1.0.0 | **Ratified**: 2026-11-08 | **Last Amended**: 2026-11-08
