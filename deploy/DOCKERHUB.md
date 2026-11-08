# Triage

Sorts newly requested movies into the right **Radarr** library — with your own rules, a local AI
(**Ollama**), and you in the loop whenever it is not sure.

Requests from **Overseerr / Jellyseerr** land in an intake root folder. Triage scores each movie
against your categories (genres, keywords, production companies, age ratings, language), asks the
local AI only for ambiguous movies, and moves it to the right library — or keeps it aside and sends
you an email with one-click choices.

- Your own categories (*Movies / Animation* is just a preset)
- Preview mode by default; never moves on doubt; never deletes anything
- Every decision explained; scans of whole folders; corrections
- Requests keep working: only the root folder changes, through Radarr's editor
- Phone and desktop, English and French

```yaml
services:
  triage:
    image: sharkhunterr/triage:latest
    ports: ["9393:9393"]
    volumes: ["./config:/config"]
    environment: [TZ=Europe/Paris, PUID=1000, PGID=1000]
    restart: unless-stopped
```

Open `http://<host>:9393`, create your account, connect Radarr and pick the intake folder, apply the
preset, scan, then switch to automatic. `TRIAGE_DEMO=1` runs a built-in demo library.

Source and documentation: https://github.com/sharkhunterr/triage
