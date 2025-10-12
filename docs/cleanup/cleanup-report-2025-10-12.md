# Cleanup Report — 2025-10-12

Branch: `optimization/cleanup-2025-10-12`

Scope: Remove unused/redundant code and scripts while preserving datasets, migrations, auth, and integrations. Verify builds and tests.

## Removed

- Files
  - `package.json` (repo root) — unused; frontend has its own `frontend/package.json`.
  - `rewrite_intelligence.py` — empty/unused.
  - `frontend/requirements.txt` — unused for React app (npm managed).
  - `backend/backend/data/skills_dynamic.json` — stray duplicate; canonical path remains `backend/data/skills_dynamic.json` via `SKILLS_DYNAMIC_PATH`.

- Scripts (trimmed)
  - Removed `eject` from `frontend/package.json`.

- Dependencies
  - None removed at this stage (kept stability; optional features like scraping/NER/LLM still referenced by code and docs).

## Consolidations

- `backend/app/services/generation.py`: unified into a single provider-switched implementation (Google Gemini primary, optional HF). API: `generate(question: str, contexts: list[str], max_new_tokens: int = 256) -> str`.

## Not Touched (by design)

- Resume datasets: `resumedataset/`, `real resumes/`, `resumes/`, `uploaded_resumes/`
- DB migrations (Alembic)
- Auth/authorization code
- Active integrations (Chroma, Google GenAI, Selenium, etc.)

## Verification

- Backend tests: PASS (12 passed)
- Frontend build (CRA): PASS (production build compiled)

## Environment files

- `.env.example` and `.env.production.example` already grouped and commented; variables match code usage. No removals needed.

## Next (optional)

- Deeper dependency pruning with import usage analysis if desired.
- CI linting/formatting pass and type checks if adding tooling.
