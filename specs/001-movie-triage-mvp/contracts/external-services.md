# Contract: calls Triage makes to external services

Each service sits behind an adapter (`triage.adapters.<service>`) with a fake used by the
tests (Constitution VIII). Only the calls listed here are allowed.

## Radarr API v3 (header `X-Api-Key`)

| Call | Use | Notes |
|---|---|---|
| `GET /api/v3/system/status` | connection test | |
| `GET /api/v3/rootfolder` | pickers, validation, FR-022h | uses `path`, `accessible`, `freeSpace` |
| `GET /api/v3/movie` | poll and scans | uses `id, tmdbId, title, year, rootFolderPath, path, genres, keywords, studio, certification, originalLanguage.name, overview, remotePoster, hasFile` |
| `GET /api/v3/movie/{id}` | confirm a move | `rootFolderPath` must equal the target |
| `PUT /api/v3/movie/editor` | move | body exactly `{"movieIds":[id],"rootFolderPath":target,"moveFiles":true,"deleteFiles":false,"addImportExclusion":false}` |

Forbidden: any `DELETE`, `POST /api/v3/movie`, `PUT /api/v3/movie/{id}`, commands.

## TMDB API v3 (bearer read token or `api_key` query)

| Call | Use |
|---|---|
| `GET /3/configuration` | connection test |
| `GET /3/movie/{tmdbId}?append_to_response=keywords,release_dates` | `genres[].id/name`, `keywords.keywords[].name`, `production_companies[].name`, `original_language`, `release_dates.results[].release_dates[].certification` |

Rate limit: ≤ 4 requests/s; responses cached 7 days per tmdbId.

## Ollama

| Call | Use |
|---|---|
| `GET /api/tags` | connection test, model list |
| `POST /api/chat` | `{"model", "messages":[system, user], "stream": false, "format": <schema>, "options": {"temperature": 0}}` |

Response schema enforced through `format`:

```json
{
  "type": "object",
  "properties": {
    "category": { "type": "string", "enum": ["<category keys>", "unsure"] },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "reasoning": { "type": "string", "maxLength": 600 }
  },
  "required": ["category", "confidence", "reasoning"]
}
```

An answer that fails validation, a timeout, or an HTTP error is recorded as
`ai.error` and the decision continues on rules alone (Constitution IV).

## Seerr — Overseerr / Jellyseerr (header `X-Api-Key`)

| Call | Use |
|---|---|
| `GET /api/v1/status` | connection test |
| `GET /api/v1/request?filter=all&take=100&skip=…&sort=modified` | find the request of a moved movie (`media.tmdbId`, `requestedBy`, `status`) |

Never called: `PUT /api/v1/request/{id}` (409 on non-pending requests, and its
`afterUpdate` re-sends to Radarr), `POST /api/v1/request/{id}/{status}`, any `DELETE`.

## SMTP (aiosmtplib)

One message per processing run that held at least one movie; multipart HTML + text; posters
as remote images (no attachments); `List-Unsubscribe` not used (single owner). Failure →
`send_email` work item retried with backoff.
