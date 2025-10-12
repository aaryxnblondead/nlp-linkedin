# Phase 1: Codebase Index (Frontend + Backend)

Date: 2025-10-12

This document summarizes the discovered modules, dependencies, routes, models, and usage relationships to inform safe cleanup in later phases.

## Frontend (React)

Root: `frontend/src`

- Entry: `index.js` -> `App.js`
- Routing: `App.js` sets up routes for `/`, `/login`, `/applicant`, `/recruiter`.
  - Uses `react-router-dom@^6`.
- Components
  - `Home.js`: Landing, CTA
  - `AuthForms.js`: `Login`, `Register` (Form components)
  - `ApplicantForm.js`: Upload resume, form fields
  - `ApplicantDashboard.js`: Shows processing state and analysis panel
  - `RecruiterDashboard.js`: Table of applicants with filters and details
  - `ScoreBreakdownRadar.js`: Radar chart (chart.js + react-chartjs-2)
  - `SummaryCell.js`: Compact KPI and pills for applicant summary
- API client
  - `src/api/apiClient.js` exposes:
    - `registerUser`, `loginUser`
    - `fetchMyApplicant`, `fetchApplicant`, `fetchAllApplicants`, `fetchScoringBreakdown`
    - `submitApplicant`, `reprocessApplicant` (currently no UI button calls `reprocessApplicant`)
- CSS: `index.css` (global styles), imported by `ApplicantDashboard.js` and `index.js`

External deps (from `frontend/package.json`): react, react-dom, axios, react-router-dom, chart.js, react-chartjs-2, react-scripts.

Observed usage
- All components listed above are imported and rendered through router paths; no dead components detected.
- `reprocessApplicant` not currently used by UI; keep for potential admin tooling.

## Backend (FastAPI)

Root: `backend/app`

- Entry: `main.py`
  - Loads `.env` via python-dotenv if present.
  - CORS configured from `FRONTEND_ORIGIN`, `EXTRA_CORS_ORIGINS`, optional `CORS_ORIGIN_REGEX`.
  - Routes included: `api/v1/endpoints/applicants.py`, `api/v1/endpoints/auth.py`.
  - Health: `/api/v1/health`, RAG status: `/api/v1/rag/status`.

- Config: `core/config.py`
  - Database URL from POSTGRES_* env vars
  - Feature flags: USE_GENERATOR, CHAT_GROUNDED_ONLY, USE_LLM_*, USE_OFFLINE_EMBEDDINGS, etc.
  - Paths: CHROMA_DIR, SKILLS_DYNAMIC_PATH

- Database models: `models/`
  - `user.py`: `User` with `UserRole` enum (applicant|recruiter)
  - `applicant.py`: `Applicant`, `Resume`, `LinkedInProfile`, `Insights`
  - `chat.py`: `ChatSession`, `ChatMessage` (no current API endpoints; reserved for chat features)

- DB session: `db.py` (SQLAlchemy engine/session)

- API endpoints: `api/v1/endpoints/`
  - `auth.py`: `/register/` and `/login/` (JWT with HS256 SECRET_KEY)
  - `applicants.py`:
    - `/me/applicant` (auto-link to user by name/email if needed)
    - `POST /applicants/` (submit applicant; enqueues Celery task; sync fallback)
    - `GET /applicants/{id}` (details)
    - `POST /applicants/{id}/reprocess` (re-run pipeline)
    - `POST /applicants/{id}/linkedin/import` (paste JSON to recompute insights)
    - `POST /applicants/{id}/linkedin/scrape_test` (role-gated; requires LinkedIn credentials in env)
    - `GET /applicants/` (recruiter list with filters)
    - `GET /applicants/{id}/scoring_breakdown` (chart data)

- Services: `services/`
  - `embeddings.py`: Chroma + Google/HF embeddings; offline-first option
  - `generation.py`: LLM generation (Google Gemini preferred; HF fallback if configured)
  - `ner.py`: spaCy+regex resume entity extraction, optional LLM assistance
  - `ner_ai_enrich.py`: LLM snippet classifier to augment entities
  - `normalize.py`: normalize structured resumes and canonicalize skills
  - `skills_dict.py`: dynamic skills alias store (JSON at `SKILLS_DYNAMIC_PATH`)
  - `storage.py`: storage abstraction (Local | Firebase stub)

- Worker: `worker/`
  - `celery_app.py`: Celery configuration (Redis broker/backend)
  - `tasks/processing_pipeline.py`: main ingestion pipeline
  - `tasks/intelligence_engine.py`: scoring and insights generation; no LLM dependency for scoring

External deps (from `backend/requirements.txt`)
- fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, python-dotenv
- passlib[argon2], python-jose[cryptography], pydantic, python-multipart
- celery, spacy, PyMuPDF, python-docx, selenium, linkedin-scraper, pytest, google-generativeai

## Notable findings (early)

- `services/generation.py` contains two implementations and duplicate function names. The latter definition overwrites the former; we will consolidate to a single implementation (keep the latter interface: `generate(question, contexts, max_new_tokens=256) -> str`). Call sites already pass `(str, [])`, which works as contexts.
- `worker/celery_app.py` hardcodes `redis://localhost:6379/0`. In Docker, REDIS_URL should be used. We will read from `REDIS_URL` env with sensible defaults.
- Dev scripts (`start_backend.ps1`, `start_all.ps1`, `start_all.cmd`) include hardcoded secrets or non-functional environment assignments. We will remove secrets and rely on `.env`/process env.
- Root `package.json` (at repo root) appears unused by the frontend (which has its own `frontend/package.json`). Flagged for potential removal.
- Sensitive files present in repo (examples): `.env`, `.env.production`, and `gen-lang-client-*.json` include real keys. These should be redacted and moved to secret management; we will not delete them automatically but will sanitize examples and scripts.

## Data preservation notes

- Resume datasets under `resumedataset/`, `real resumes/`, `resumes/` and dynamic skills JSON must be preserved. No deletions planned for any data files.

---
This index will be refined as we proceed with Phases 2–5. See `usage-summary.md` for current render/import usage and potential dead code.
