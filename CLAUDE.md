# Triage

## Git

- Commits use the repository owner's configured Git identity: never change `git user.name` / `git user.email`, never use Claude Code or Anthropic as author.
- Never add a "Co-Authored-By" line, nor any mention of Claude, Claude Code or Anthropic (no "Generated with…" text) in commit messages, merge requests or code.
- Never push, force-push, rewrite published history, delete branches or create releases unless explicitly asked.
- Bugs, features and ideas are tracked as issues on the local GitLab: http://192.168.1.60/root/triage

## Language

- Code, README, release notes and the Docker Hub page are written in English.
- The interface speaks English and French.

## Active Technologies
- Python 3.12 (backend), TypeScript 5.9 on Node 22 LTS (frontend) + FastAPI, Pydantic 2, SQLAlchemy 2 async + aiosqlite, Alembic, httpx, aiosmtplib, argon2-cffi, uvicorn; React 19, Vite 7, TanStack Query, React Router, Radix UI, Tailwind 4, lucide-react, react-intl, openapi-typescript (001-movie-triage-mvp)
- SQLite file in `/config` (WAL mode); no other datastore (001-movie-triage-mvp)

## Recent Changes
- 001-movie-triage-mvp: Added Python 3.12 (backend), TypeScript 5.9 on Node 22 LTS (frontend) + FastAPI, Pydantic 2, SQLAlchemy 2 async + aiosqlite, Alembic, httpx, aiosmtplib, argon2-cffi, uvicorn; React 19, Vite 7, TanStack Query, React Router, Radix UI, Tailwind 4, lucide-react, react-intl, openapi-typescript
