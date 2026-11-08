# Data Model: Triage MVP

SQLite (one file, `/config/triage.db`), SQLAlchemy 2 async, Alembic migrations. Timestamps are
stored as UTC ISO-8601. Identifiers are integers (autoincrement) unless stated. Secrets are
stored server-side only and never serialized to API responses (Constitution VII).

## Entities

### `owner`
Single row: the account allowed to sign in.

| Field | Type | Rules |
|---|---|---|
| id | int | always 1 |
| username | text | 3–64 chars |
| password_hash | text | argon2id |
| locale | text | `en` \| `fr`, default from browser at setup |
| created_at | datetime | |

### `session`
| Field | Type | Rules |
|---|---|---|
| id_hash | text PK | SHA-256 of the random cookie value |
| created_at, last_seen_at, expires_at | datetime | sliding 30 days |
| user_agent, ip | text | for the sessions list |

### `setting`
Key–value store for scalar settings, typed and validated by a Pydantic settings model.

| Key | Type | Default |
|---|---|---|
| radarr.url / radarr.api_key* | str | — |
| radarr.intake_root_folders | list[str] | [] (must be existing Radarr root folders) |
| tmdb.api_key* | str | "" (optional) |
| ollama.url / ollama.model | str | "" (AI disabled when empty) |
| ollama.timeout_s | int | 60 |
| ai.weight | int 0–100 | 60 |
| seerr.url / seerr.api_key* | str | "" (optional) |
| seerr.webhook_secret* | str | generated at setup |
| smtp.host / port / security / username / password* / from / to | … | — (email off when empty) |
| app.base_url | str | used in email links |
| triage.mode | `preview` \| `automatic` | `preview` |
| triage.threshold | float 0.5–1 | 0.80 |
| triage.margin | int 0–100 | 20 |
| triage.poll_interval_s | int ≥ 60 | 300 |
| triage.link_validity_days | int 1–30 | 7 |

\* secret: write-only through the API; reads return `{ "set": true|false }`.

### `category`
| Field | Type | Rules |
|---|---|---|
| id | int | |
| key | text | slug, unique, stable (used by the AI schema) |
| name | text | 1–60 chars, unique |
| description | text | ≤ 1000 chars, sent to the AI |
| root_folder_path | text | an existing Radarr root folder, not an intake folder |
| is_fallback | bool | at most one category true |
| position | int | display / tie-break order |
| version | int | +1 on every edit of this category or its rules |
| deleted_at | datetime? | soft delete: history keeps referring to it |

### `rule`
| Field | Type | Rules |
|---|---|---|
| id | int | |
| category_id | FK category | |
| field | enum | `genre`, `keyword`, `company`, `certification`, `original_language` |
| operator | enum | `is`, `contains`, `is_not` (`is_not` scores when absent) |
| value | text | case/accent-insensitive comparison |
| weight | int 1–100 | |
| decisive | bool | a match alone settles the category |

### `movie_ref`
Triage's view of a Radarr movie (cache; Radarr stays authoritative).

| Field | Type | Rules |
|---|---|---|
| radarr_id | int PK | |
| tmdb_id | int | |
| title, year, poster_url | | refreshed on each poll |
| root_folder_path | text | as last seen |
| corrected | bool | the owner corrected an automatic move → never auto-sorted again |
| updated_at | datetime | |

### `metadata_cache`
| Field | Type | Rules |
|---|---|---|
| tmdb_id | int PK | |
| payload | JSON | normalized signals (genres, keywords, companies, certifications, language, overview) |
| fetched_at | datetime | expires after 7 days |

### `arrival`
One stay of a movie in an intake folder (idempotency key, research R10).

| Field | Type | Rules |
|---|---|---|
| id | int | |
| radarr_id | FK movie_ref | |
| intake_path | text | |
| first_seen_at | datetime | |
| closed_at | datetime? | set when the movie leaves the intake folder |
| close_reason | enum? | `moved_by_triage`, `moved_elsewhere`, `removed_from_radarr` |

Unique: one open arrival per `radarr_id`.

### `decision`
One classification (automatic, simulated, or from a scan) with everything needed to explain it.

| Field | Type | Rules |
|---|---|---|
| id | int | |
| radarr_id | FK movie_ref | |
| arrival_id | FK arrival? | null for scans of category libraries and simulations |
| scan_id | FK scan? | set for scan proposals |
| source | enum | `intake`, `scan`, `simulation` |
| signals | JSON | list of `{field, value, rule_id, category_key, weight, kind: fact}` |
| ai | JSON? | `{model, category_key, confidence, reasoning, duration_ms, error}` (`kind: inference`) |
| scores | JSON | `{category_key: score}` |
| top_category_id | FK category? | |
| confidence | float | |
| categories_snapshot | JSON | categories + rules + versions used (FR-010) |
| status | enum | see state machine |
| actor | enum | `triage`, `owner` |
| target_root_folder | text? | where it was / will be moved |
| request_check | JSON? | `{request_id, requester, status, tracked: bool, checked_at, error}` |
| error | text? | last error |
| created_at, decided_at | datetime | |

### `review_link`
| Field | Type | Rules |
|---|---|---|
| token_hash | text PK | SHA-256 of a 32-byte random token |
| decision_id | FK decision | |
| choice | text | category key or `intake` |
| expires_at | datetime | now + link validity |
| used_at | datetime? | single use; all links of a decision are revoked once it is decided |

### `scan`
| Field | Type | Rules |
|---|---|---|
| id | int | |
| root_folder_path | text | intake folder or a category library |
| state | enum | `running`, `done`, `cancelled`, `failed` |
| total, done | int | progress |
| started_at, finished_at | datetime | |

### `work_item`
Persistent queue of the single in-process worker (research R9).

| Field | Type | Rules |
|---|---|---|
| id | int | |
| kind | enum | `classify`, `move`, `verify_request`, `send_email`, `scan_movie` |
| ref | JSON | ids the job needs (decision, arrival, scan…) |
| state | enum | `pending`, `running`, `done`, `failed` |
| attempts | int | max 8 |
| next_attempt_at | datetime | exponential backoff 1 min → 1 h |
| last_error | text? | shown on the status page |

### `audit_event`
Append-only log of every move and owner action (FR-031).

| Field | Type |
|---|---|
| id, at, actor (`triage`/`owner`), action, radarr_id, decision_id, from_path, to_path, result, detail |

## Decision state machine

```text
                ┌──────────── simulation ───────────► simulated (never moves)
classify ───────┤
                ├─ confident & automatic ─► moving ─► moved ─► (owner) corrected
                │                              └──► failed (retry) ─► moving
                ├─ confident & preview ───► proposed ─► (owner apply) ─► moving
                │                               └──► (owner dismiss) ─► dismissed
                └─ not confident ─────────► held ─► (owner choice / link) ─► moving
                                                 └──► (owner "leave") ─► left_in_intake
scan proposal ──► proposed | in_place ─► (owner apply) ─► moving
```

- `moving → moved` only after Radarr reports the new `rootFolderPath` (research R2).
- Any state ends as `superseded` when the arrival closes for another reason (movie moved or
  removed outside Triage) before a move — no action is taken.
- `held` and `proposed` revoke all their `review_link`s when they leave the state.

## Validation rules (from the spec)

- A category's `root_folder_path` MUST exist in Radarr and MUST NOT be an intake folder
  (FR-006); at most one fallback (FR-008).
- Intake folders MUST exist in Radarr; a movie outside them is never classified except in an
  owner-started scan or simulation (FR-003).
- A decision moves only if `confidence ≥ threshold` and `score_top − score_second ≥ margin`
  and mode is `automatic`, or the owner applied it (FR-015, FR-022).
- `movie_ref.corrected = true` excludes the movie from automatic sorting (FR-021).
