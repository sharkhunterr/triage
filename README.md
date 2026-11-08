# Triage

Triage sorts newly requested movies into the right Radarr library.

Requests made by household members in Overseerr or Jellyseerr land in an *intake* root folder.
Triage reads each new movie's metadata, applies **your own categories** (for example *Movies*
and *Animation*, or anything else), asks a **local AI** (Ollama) when the metadata is not
conclusive, and either moves the movie to the matching library or keeps it aside and asks you.

- **Safe by default** — starts in preview mode; never moves on doubt; never deletes anything.
- **Explainable** — every decision shows the signals it used and why.
- **One tap** — doubtful movies come with an email and a review queue to decide in one tap.
- **Scans** — check a whole folder (the intake backlog or an existing library) and apply the
  moves you agree with.

> Work in progress — see `specs/001-movie-triage-mvp/` for the specification and plan.
