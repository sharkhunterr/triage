# Feature Specification: Triage MVP — sort newly requested movies into the right library

**Feature Branch**: `001-movie-triage-mvp`
**Created**: 2026-11-08
**Status**: Draft
**Input**: User description: "Triage MVP — automatic sorting of newly requested movies into
user-defined Radarr libraries. Requests from non-admin users land in an intake root folder
('Nouveaux/Non Triés'); today the owner moves each one by hand to 'Films' or 'Dessins Animés'.
Triage classifies each movie from its metadata and a local AI, moves it when confident, holds
it and notifies the owner (email + web) when in doubt. Categories are user-defined; movies
only; single Docker image. Follow-up: a preview mode to see what Triage would do before it
acts; a scan mode for the movies already present in a folder; moves must not break the
request portal's (Overseerr/Jellyseerr) requests."

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

### User Story 4 - Preview what Triage would do before it acts (Priority: P1)

The owner does not want Triage to touch the library until they trust it. In preview mode,
Triage classifies every movie as usual but moves nothing: each movie shows the category it
would go to, the confidence, and the reasons. From the preview list the owner can apply one
proposal, apply all confident proposals at once, choose another category, or dismiss. When
satisfied, the owner switches to automatic mode. The owner can also ask "what would you do
with this movie?" for any single movie before anything happens.

**Why this priority**: the safety net that lets the owner check Triage's judgement on their
own library before letting it act.

**Independent Test**: in preview mode, add movies to the intake folder; check none moves,
each shows its proposed category and reasons, and "apply" on one moves only that one.

**Acceptance Scenarios**:

1. **Given** preview mode, **When** movies arrive in the intake folder, **Then** none is moved
   and each appears in the preview list with its proposed category, confidence, and reasons.
2. **Given** proposals in the preview list, **When** the owner applies one, applies all
   proposals at or above the threshold, or picks another category, **Then** exactly those
   movies are moved and recorded as decided by the owner.
3. **Given** preview mode, **When** the owner switches to automatic mode, **Then** only movies
   arriving afterwards are moved automatically; pending proposals stay for the owner to apply
   or dismiss.
4. **Given** a single movie, **When** the owner asks Triage to simulate its decision, **Then**
   the proposed category and reasons are shown and nothing is moved or recorded as a move.

---

### User Story 5 - Scan movies already in a folder (Priority: P1)

At first start, the intake folder already holds a backlog, and the owner suspects some movies
in "Films" are actually animated. The owner starts a scan of a chosen folder: the intake
folder (default) or any category's library. Triage classifies every movie in it and shows the
results as a preview — never moving anything by itself — listing for each movie its current
library, the proposed category, the confidence, and the reasons. The owner applies the moves
they agree with, individually or all confident ones at once.

**Why this priority**: the existing backlog and past manual mistakes are where the owner sees
value on day one.

**Independent Test**: start a scan of a library holding a misplaced animated movie; check the
scan proposes moving it, moves nothing on its own, and moves it when the owner applies.

**Acceptance Scenarios**:

1. **Given** movies already in the intake folder, **When** the owner scans it, **Then** each
   movie gets a proposal and nothing is moved until the owner applies.
2. **Given** a category's library, **When** the owner scans it, **Then** movies whose proposal
   matches their current library are shown as "in place", and the others as proposed moves.
3. **Given** a scan in progress, **When** the owner looks at it, **Then** progress (movies done
   out of total) is shown and the owner can cancel it; partial results are kept.
4. **Given** scan results, **When** the owner applies all confident proposals, **Then** only
   movies at or above the threshold whose proposal differs from their current library are
   moved.

---

### User Story 6 - Requests keep working after a move (Priority: P1)

A household member requested a movie in the request portal; Triage moves it to its library.
The request still shows the movie's status (requested, downloading, available), the movie is
not downloaded twice, and it becomes available to the household in the right media library.

**Why this priority**: a sorting tool that breaks the request flow would be worse than sorting
by hand.

**Independent Test**: request a movie, let Triage move it, then check in the request portal
that the request still tracks the same movie and becomes available once downloaded.

**Acceptance Scenarios**:

1. **Given** a requested movie in the intake folder, **When** Triage moves it, **Then** the
   movie keeps the same entry in the movie manager (never removed and re-added), so the
   request portal keeps tracking it.
2. **Given** the request portal is connected, **When** a requested movie is moved, **Then** the
   request's recorded destination folder is updated to the new library where the portal
   allows it, so that re-processing the request does not send the movie back to the intake
   folder.
3. **Given** a movie is moved before it is downloaded, **When** the download completes,
   **Then** the file lands in the new library and the request becomes available.
4. **Given** the categories' libraries, **When** the owner opens the status page, **Then** it
   warns about any category library the movie manager cannot write to.

---

### User Story 7 - I can see, undo, and correct what Triage did (Priority: P2)

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

### User Story 8 - I configure the connections and see their health (Priority: P2)

From the settings, the owner connects the movie manager, the metadata provider, the request
portal (optional), the local AI (optional), and the mail server; picks the intake folder(s);
sets the confidence threshold; and chooses between preview and automatic mode. Each connection has a "test" action. A status page shows
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
4. **Given** preview mode, **When** movies are processed, **Then** every decision is recorded
   as a proposal and no movie is moved (see User Story 4).

---

### User Story 9 - Requests reach Triage immediately (Priority: P3)

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
- A movie's request is still pending approval in the request portal when Triage sees it in
  the intake folder: Triage sorts the movie; the request portal's recorded folder is updated
  if the portal allows it, otherwise the decision notes that it could not be.
- The request portal is unreachable when a movie is moved: the move still happens (the movie
  entry is unchanged, so tracking is kept); updating the request's folder is retried.
- A scan covers a large library (hundreds of movies): it runs in the background at a pace the
  connected services tolerate, and the owner can leave and come back to its results.
- A movie is proposed in a scan and arrives in the intake folder at the same time: it is
  classified once; one proposal is shown.

## Requirements *(mandatory)*

### Functional Requirements

**Intake and processing**

- **FR-001**: The system MUST periodically check the configured intake root folder(s) of the
  movie manager and pick up every movie found there that it has not processed yet. The check
  interval MUST be configurable (default: 5 minutes).
- **FR-002**: The system MUST accept an optional, secret-protected notification from the
  request portal that triggers an immediate check.
- **FR-003**: Outside a scan started by the owner, the system MUST NOT examine, move, or
  modify any movie outside the intake folders. It MUST NOT delete any movie or file, ever.
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
  back to the intake folder; a corrected movie MUST never be re-sorted automatically, though a
  scan may still propose it.
- **FR-022**: The system MUST offer two modes: **preview** (every decision is a proposal;
  nothing is moved without the owner) and **automatic** (confident movies are moved, doubtful
  ones held). The default is preview until the owner switches.
- **FR-022a**: In preview, the owner MUST be able to apply one proposal, apply all proposals
  at or above the threshold, pick another category, or dismiss a proposal.
- **FR-022b**: The owner MUST be able to simulate the decision for any single movie; a
  simulation MUST NOT move or record a move.

**Scan**

- **FR-022c**: The owner MUST be able to scan a chosen root folder (an intake folder by
  default, or any category's library). A scan MUST only produce proposals; moves happen only
  when the owner applies them.
- **FR-022d**: Scan results MUST show, per movie, its current library, the proposed category,
  the confidence, the reasons, and whether it is already in place.
- **FR-022e**: A scan MUST run in the background with visible progress, MUST be cancellable,
  and MUST keep partial results.

**Request portal**

- **FR-022f**: Moving a movie MUST only change its library in the movie manager; the movie
  entry MUST never be removed and re-added, so requests keep tracking it.
- **FR-022g**: When the request portal is connected, the system MUST update the moved movie's
  request so its recorded destination folder is the new library, where the portal allows it;
  a failure to do so MUST be recorded on the decision and retried, and MUST NOT undo the move.
- **FR-022h**: The status page MUST warn when a category's library is missing from the movie
  manager or reported as not accessible by it.

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
  provider key, request portal connection (optional), local AI address and model (optional),
  mail server and recipient, confidence threshold, check interval, AI timeout, link validity,
  and the preview / automatic mode.
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
- **Scan**: an owner-started classification of one root folder — folder, start and end time,
  progress, state (running, done, cancelled), and one proposal per movie.
- **Proposal**: what Triage would do with a movie (category, confidence, reasons) without
  having done it; applied, changed, or dismissed by the owner. Preview-mode decisions and scan
  results are proposals.
- **Request link**: the request portal's request for a movie, if any, and whether its recorded
  folder was updated after a move.
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
- **SC-008**: In preview mode and during scans, zero movies are moved without an explicit
  owner action.
- **SC-009**: 100 % of requests whose movie Triage moved keep tracking it and become available
  once downloaded, with no duplicate download.
- **SC-010**: A scan of a 500-movie library completes in under 30 minutes without making the
  connected services unavailable.

## Assumptions

- The movie manager is Radarr; the request portal is Overseerr or Jellyseerr, already
  configured to send non-admin requests to the intake root folder. The metadata provider is
  TMDB (the owner supplies an API key). The local AI is an Ollama server, optional.
- Triage serves a single owner account (created on first start); household members only use
  the request portal and never sign in to Triage.
- Movies only; TV series, cloud AI providers, and other notification channels (Discord, push)
  are out of scope for this MVP.
- Triage starts in preview mode, and the owner is invited to scan the intake folder first,
  so they can check its judgement on the existing backlog before switching to automatic.
- The request portal tracks a movie through the movie manager's entry, so changing only the
  movie's folder keeps the request linked; the portal's API may only allow editing the
  recorded folder of some requests (for example pending ones), which is why updating it is
  best-effort (FR-022g).
- The media server (Plex/Jellyfin) libraries already include every category's folder, so
  moved movies become available there; Triage does not manage media server libraries.
- The owner's movie manager root folders already exist; Triage does not create folders.
- Decision history is kept indefinitely (it is small); the owner can purge entries older than
  a chosen date.
- Emails are sent to one configured recipient address; decision links point to the address
  at which the owner reaches Triage (configured base URL).
