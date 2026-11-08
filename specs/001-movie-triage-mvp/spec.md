# Feature Specification: Triage MVP — sort newly requested movies into the right library

**Feature Branch**: `001-movie-triage-mvp`
**Created**: 2026-11-08
**Status**: Draft
**Input**: User description: "Triage MVP — automatic sorting of newly requested movies into
user-defined Radarr libraries. Requests from non-admin users land in an intake root folder
('Nouveaux/Non Triés'); today the owner moves each one by hand to 'Films' or 'Dessins Animés'.
Triage classifies each movie from its metadata and a local AI, moves it when confident, holds
it and notifies the owner (email + web) when in doubt. Categories are user-defined; movies
only; single Docker image."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confident movies are sorted without me (Priority: P1)

A household member requests a movie through the request portal. It lands in the intake
folder. Within minutes, Triage reads its metadata, recognizes it clearly belongs to one of the
owner's categories (for example an animated Pixar film → "Dessins Animés", a live-action
thriller → "Films"), and moves it to that category's library. The owner never has to open the
movie manager for it.

**Why this priority**: this is the chore Triage exists to remove; with only this story, most
requests are already handled.

**Independent Test**: configure two categories with their rules, add a clearly animated movie
and a clearly live-action movie to the intake folder, and check each ends up in the expected
library with a recorded decision.

**Acceptance Scenarios**:

1. **Given** categories "Films" and "Dessins Animés" and auto-move enabled, **When** a movie
   whose metadata strongly indicates animation appears in the intake folder, **Then** it is
   moved to the "Dessins Animés" library and the decision lists the signals that led to it.
2. **Given** the same setup, **When** a movie with no animation signal and a live-action
   description appears, **Then** it is moved to "Films".
3. **Given** a movie was already processed, **When** Triage checks the intake folder again or
   restarts, **Then** the movie is not processed, moved, or notified a second time.
4. **Given** a movie sits in a root folder that is not an intake folder, **When** Triage runs,
   **Then** the movie is never examined or moved.

---

### User Story 2 - Doubtful movies wait for me, and I decide in one tap (Priority: P1)

Triage meets a movie it cannot classify confidently (an adult animated film, a film mixing
live action and animation, conflicting signals). It leaves the movie in the intake folder,
adds it to the review queue, and emails the owner with the movie, the reasons for the doubt,
and one link per category. The owner taps a link from the email (or a button in the review
queue on their phone) and the movie is moved to that library.

**Why this priority**: never moving on doubt is the safety promise; without a fast way to
settle doubts, held movies would pile up.

**Independent Test**: add a movie with conflicting signals; check it stays in the intake
folder, appears in the review queue, triggers one email, and that choosing a category from
the email link or the queue moves it.

**Acceptance Scenarios**:

1. **Given** a movie whose confidence is below the threshold, **When** it is processed,
   **Then** it stays in the intake folder, appears in the review queue with its reasons, and
   one email is sent containing the reasons and one decision link per category.
2. **Given** a held movie, **When** the owner opens a decision link from the email, **Then**
   the movie is moved to the chosen category, the review item is closed, and the link cannot
   be used again.
3. **Given** a decision link older than its validity period, **When** it is opened, **Then**
   nothing is moved and the page offers to decide from the review queue instead.
4. **Given** a held movie, **When** the owner picks a category in the review queue, **Then**
   it is moved and the matching email links stop working.
5. **Given** a held movie, **When** the owner chooses "leave in intake", **Then** the movie is
   not moved and is not proposed again.

---

### User Story 3 - I define my own categories and rules (Priority: P1)

On first start the owner picks the "Movies / Animation" preset or starts empty, then edits
categories: name, target library (chosen from the movie manager's existing root folders), a
plain-language description used by the AI, and rules (genres, keywords, production companies,
certification, original language) with how strongly each counts. One category can be the
fallback used when no other category's signals are present. The owner can add a third
category (for example "Documentaires") without anything else changing.

**Why this priority**: without categories nothing can be sorted; making them configurable is
what keeps Triage generic.

**Independent Test**: create a new category with its own rules and library, add a matching
movie, and check it is sorted there.

**Acceptance Scenarios**:

1. **Given** an empty configuration, **When** the owner applies the "Movies / Animation"
   preset, **Then** two editable categories are created with sensible rules, and the owner
   only has to pick their target libraries.
2. **Given** existing categories, **When** the owner adds a category with its own rules and
   library, **Then** subsequent movies matching those rules go to that library.
3. **Given** a category's library is chosen, **When** the list of libraries is shown, **Then**
   it contains only the movie manager's existing root folders, and intake folders cannot be a
   category's target.
4. **Given** past decisions, **When** a category is renamed, edited, or deleted, **Then** past
   decisions still show the category and rules as they were when decided.

---

### User Story 4 - I can see, undo, and correct what Triage did (Priority: P2)

The owner opens Triage from a phone or a computer and sees recent decisions: what was moved
where, what is waiting, and why. For any automatic move, the owner can move the movie back to
the intake folder or to another category; the correction is recorded.

**Why this priority**: trust in automation depends on being able to check and fix it; the
system is still useful without it, but less trustworthy.

**Independent Test**: let Triage move a movie, then use "move to another category" from the
history and check the movie changed library and the history shows both decisions.

**Acceptance Scenarios**:

1. **Given** decisions exist, **When** the owner opens the dashboard, **Then** they see counts
   of moved, held, and failed movies and the latest decisions with their outcome.
2. **Given** an automatic move, **When** the owner opens it, **Then** they see every signal
   observed, its weight, the AI verdict and reasoning if consulted, the final confidence, and
   which elements are metadata facts versus AI interpretation.
3. **Given** an automatic move, **When** the owner moves it to another category or back to the
   intake folder, **Then** the movie is moved accordingly and the history keeps both the
   automatic decision and the correction.
4. **Given** a movie the owner has corrected, **When** Triage runs again, **Then** it never
   re-sorts that movie automatically.

---

### User Story 5 - I configure the connections and see their health (Priority: P2)

From the settings, the owner connects the movie manager, the metadata provider, the local AI
(optional), and the mail server; picks the intake folder(s); sets the confidence threshold;
and turns automatic moving on or off. Each connection has a "test" action. A status page shows
whether each service is reachable, the last processing run, and items that failed.

**Why this priority**: required to run, but simple; the defaults make it a one-time task.

**Independent Test**: enter connection details, run each test, and check the status page
reflects a reachable and an unreachable service.

**Acceptance Scenarios**:

1. **Given** the settings page, **When** the owner enters connection details and runs "test",
   **Then** the result says whether the service is reachable and why not if it is not.
2. **Given** saved secrets (API keys, mail password), **When** the settings page is reopened,
   **Then** it shows that each secret is set without ever displaying or sending its value.
3. **Given** the local AI is unreachable, **When** a movie is processed, **Then** it is decided
   on rules alone, or held if the rules are not conclusive, and the status page shows the AI as
   unavailable.
4. **Given** automatic moving is off, **When** movies are processed, **Then** every decision is
   recorded as a proposal and every movie goes to the review queue instead of being moved.

---

### User Story 6 - Requests reach Triage immediately (Priority: P3)

The owner points the request portal's webhook at Triage. When a request is approved, Triage
checks the intake folder right away instead of waiting for its next scheduled check.

**Why this priority**: a convenience; periodic checks already catch every movie.

**Independent Test**: send a request-approved webhook and check processing starts within
seconds; send one without the shared secret and check it is rejected.

**Acceptance Scenarios**:

1. **Given** the webhook is configured, **When** an approved movie request notification
   arrives, **Then** Triage checks the intake folders within a few seconds.
2. **Given** a webhook call without the configured secret, **When** it arrives, **Then** it is
   rejected and nothing is processed.

---

### Edge Cases

- A movie is still downloading or not yet downloaded when it is sorted: the move only changes
  where the movie manager will keep it; no file is lost and later downloads land in the new
  library.
- The movie manager, metadata provider, AI, or mail server is down or slow: no movie is moved
  on partial information; work is retried with increasing delay; items failing repeatedly are
  shown as failed with the reason.
- The owner moves a movie out of the intake folder by hand before Triage handles it: Triage
  leaves it alone.
- A movie has no metadata match (unknown to the metadata provider, empty genres): it is held
  for review with that reason.
- Two categories both match strongly: the movie is held, never assigned arbitrarily.
- A category's target library no longer exists in the movie manager: movies for it are held,
  and the category is flagged in the interface.
- The mail server is unavailable when a movie is held: the movie is still in the review queue,
  and the email is retried.
- Many movies arrive at once (a backlog in the intake folder at first start): they are
  processed one after another without overwhelming the connected services, and held movies
  are grouped into a single email per processing run rather than one per movie.
- The same email decision link is opened twice, or after the movie was decided in the
  interface: the second use does nothing and says the movie was already decided.

## Requirements *(mandatory)*

### Functional Requirements

**Intake and processing**

- **FR-001**: The system MUST periodically check the configured intake root folder(s) of the
  movie manager and pick up every movie found there that it has not processed yet. The check
  interval MUST be configurable (default: 5 minutes).
- **FR-002**: The system MUST accept an optional, secret-protected notification from the
  request portal that triggers an immediate check.
- **FR-003**: The system MUST NOT examine, move, or modify any movie outside the intake
  folders, and MUST NOT delete any movie or file.
- **FR-004**: Processing MUST be idempotent: a movie MUST be processed once per arrival in an
  intake folder, even across restarts or repeated checks.
- **FR-005**: A movie that leaves the intake folder by any other means before being sorted
  MUST be dropped from processing without action.

**Categories**

- **FR-006**: The owner MUST be able to create, edit, reorder, and delete categories. Each
  category has a name, a target library (one of the movie manager's root folders, never an
  intake folder), a plain-language description, and a set of rules.
- **FR-007**: A rule MUST match on one of: genre, keyword, production company, certification,
  or original language; MUST carry a weight; and MAY be marked decisive (a match alone settles
  the category).
- **FR-008**: One category MAY be marked as fallback: it is chosen when no other category's
  signals are present and the AI (if enabled) does not contradict it.
- **FR-009**: The system MUST offer a "Movies / Animation" preset that creates two editable
  categories with rules for animation (genre, keywords such as anime and stop-motion,
  well-known animation studios) and a fallback category for everything else.
- **FR-010**: Past decisions MUST keep the category definition in force when they were made.

**Classification**

- **FR-011**: For each movie the system MUST gather its metadata (genres, keywords, production
  companies, certification, original language, overview) from the metadata provider.
- **FR-012**: The system MUST evaluate the category rules first and compute, for each
  category, a score and an overall confidence.
- **FR-013**: When the local AI is enabled and the rules are not conclusive, the system MUST
  ask the AI to choose among the categories using their descriptions and the movie's
  metadata, and MUST record its choice, its stated reasoning, and its confidence as an
  additional signal.
- **FR-014**: The AI MUST NOT override a decisive rule. If the AI is disabled, unreachable,
  times out (configurable, default 60 seconds), or answers something unusable, the decision
  MUST rely on rules alone.
- **FR-015**: If the top category's confidence is at or above the configured threshold
  (default: 80 %) and no other category is close behind, the movie MUST be moved; otherwise it
  MUST be held for review.

**Moving and review**

- **FR-016**: Moving a movie MUST change its root folder in the movie manager to the
  category's library and let the movie manager move existing files.
- **FR-017**: A held movie MUST stay in the intake folder and appear in the review queue with
  the reasons for the doubt.
- **FR-018**: For each processing run that holds at least one movie, the system MUST send one
  email listing each held movie with its poster, its reasons, and one decision link per
  category plus a "leave in intake" link.
- **FR-019**: Decision links MUST be signed, single-use, and expire after a configurable
  period (default: 7 days).
- **FR-020**: From the review queue, the owner MUST be able to choose a category or leave the
  movie in the intake folder in one action.
- **FR-021**: The owner MUST be able to move any movie Triage moved to another category or
  back to the intake folder; a corrected movie MUST never be re-sorted automatically.
- **FR-022**: An "automatic moving" switch MUST exist; when off, every movie is held as a
  proposal (default: off until the owner turns it on after setup).

**Interface**

- **FR-023**: The interface MUST provide: a dashboard (counts and recent decisions), the
  review queue, decision history with search and filters (outcome, category, date), decision
  detail, the category editor, settings, and a status page.
- **FR-024**: Every screen MUST be fully usable on a smartphone and on a desktop, in English
  and in French, with keyboard and touch, in light and dark themes.
- **FR-025**: Decision detail MUST distinguish metadata facts from AI interpretation.
- **FR-026**: Empty and error states MUST tell the owner what will appear there or what to do
  next.

**Settings, security, health**

- **FR-027**: Settings MUST cover: movie manager connection and intake folder(s), metadata
  provider key, local AI address and model (optional), mail server and recipient, confidence
  threshold, check interval, AI timeout, link validity, and the automatic moving switch.
  Each connection MUST have a test action.
- **FR-028**: The interface MUST require the owner to sign in. Secrets MUST never be displayed
  or sent to the browser once saved.
- **FR-029**: Failed operations MUST be retried with increasing delay; an item still failing
  after the retries MUST appear as failed with its reason and a retry action.
- **FR-030**: A status page MUST show each connected service's health, the last and next
  processing run, and the number of held and failed items.
- **FR-031**: The system MUST keep a log of every decision and every move, with the date, the
  actor (automatic or owner), and the result.

### Key Entities

- **Category**: a destination defined by the owner — name, target library, description for
  the AI, rules, optional fallback flag, order.
- **Rule**: a condition on one metadata field (genre, keyword, company, certification,
  original language) with a weight and an optional decisive flag; belongs to a category.
- **Movie (as seen by Triage)**: a reference to a movie in the movie manager — its identifier,
  title, year, poster, metadata identifier, and the intake folder it arrived in.
- **Decision**: one classification of one arrival of a movie — signals observed with weights,
  AI verdict and reasoning if consulted, per-category scores, confidence, outcome (moved,
  held, proposal, failed, corrected, left in intake), snapshot of the categories used, actor,
  timestamps.
- **Review item**: a held movie awaiting the owner's choice, with its decision links and their
  state (unused, used, expired).
- **Settings**: connections, intake folders, thresholds, intervals, switches; secrets stored
  server-side only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In daily use with the animation preset, at least 85 % of new movies are sorted
  without the owner doing anything.
- **SC-002**: No movie is ever moved to a wrong category with a confidence below the
  threshold; movies the owner has to correct after an automatic move stay under 2 %.
- **SC-003**: A movie arriving in the intake folder is sorted or held within 10 minutes with
  periodic checks, and within 1 minute when the request portal's notification is configured.
- **SC-004**: Settling a held movie takes the owner one tap from the email or the review queue,
  and under 10 seconds from opening it.
- **SC-005**: When the AI is unavailable, every movie is still either sorted by rules or held;
  none is lost or moved on a guess.
- **SC-006**: A first-time owner goes from starting Triage to the first automatic sort in
  under 10 minutes using the preset.
- **SC-007**: Every screen is complete and usable on a 360-pixel-wide phone screen and on a
  desktop, in both languages.

## Assumptions

- The movie manager is Radarr; the request portal is Overseerr or Jellyseerr, already
  configured to send non-admin requests to the intake root folder. The metadata provider is
  TMDB (the owner supplies an API key). The local AI is an Ollama server, optional.
- Triage serves a single owner account (created on first start); household members only use
  the request portal and never sign in to Triage.
- Movies only; TV series, cloud AI providers, and other notification channels (Discord, push)
  are out of scope for this MVP.
- Automatic moving starts off: on first start Triage proposes decisions for the movies
  already in the intake folder, so the owner can check its judgement on the existing backlog
  before turning automatic moving on.
- The owner's movie manager root folders already exist; Triage does not create folders.
- Decision history is kept indefinitely (it is small); the owner can purge entries older than
  a chosen date.
- Emails are sent to one configured recipient address; decision links point to the address
  at which the owner reaches Triage (configured base URL).
