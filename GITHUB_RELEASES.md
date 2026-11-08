# v0.1.0

## 🎬 Triage 0.1.0 — first release

Triage sorts newly requested movies into the right Radarr library. Requests from Overseerr or
Jellyseerr land in an intake root folder; Triage scores each movie against your own categories, asks
a local AI (Ollama) when the rules are not conclusive, and moves it — or keeps it aside and asks you.

### ✨ Features

- **Your own categories** — name, Radarr library, description for the AI, weighted rules on genres,
  keywords, production companies, age ratings and original language; one fallback category. A
  *Movies / Animation* preset to start.
- **Preview mode by default** — Triage proposes, you apply one proposal or all the confident ones;
  switch to automatic when you trust it.
- **Scans** — classify a whole folder (the intake backlog or an existing library); proposals only.
- **Doubt is never a move** — doubtful movies wait in the review queue; one email per run with
  single-use, expiring one-click links.
- **Explainable decisions** — facts and AI interpretation shown apart, scores per category, history.
- **Corrections** — move any sorted movie elsewhere or back to the intake folder; Triage never sorts
  it on its own again.
- **Requests keep working** — moves go through Radarr's movie editor (same movie entry); Seerr
  requests are checked, never edited.
- **Webhook** for immediate sorting, **status page**, failed-work retries.
- Mobile and desktop, English and French, light and dark themes.

### 🐳 Quick start

```yaml
services:
  triage:
    image: sharkhunterr/triage:0.1.0
    ports: ["9393:9393"]
    volumes: ["./config:/config"]
    environment: [TZ=Europe/Paris, PUID=1000, PGID=1000]
```
