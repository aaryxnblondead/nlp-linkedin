# Phase 4: Environment Configuration Audit

Date: 2025-10-12

This document maps environment variables discovered in code and Docker to a cleaned structure for `.env` (dev) and `.env.production`.

## Variables used in code

Backend (`backend/app`):
- Database: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_SERVER, POSTGRES_PORT
- CORS: FRONTEND_ORIGIN, EXTRA_CORS_ORIGINS, CORS_ORIGIN_REGEX (optional)
- NLP/LLM: USE_GENERATOR, CHAT_GROUNDED_ONLY, GENERATOR_MODEL_ID/GEMINI_MODEL_ID, GEN_PROVIDER, GOOGLE_API_KEY, HUGGINGFACE_HUB_TOKEN, HF_MODEL_ID, USE_OFFLINE_EMBEDDINGS, SPACY_MODEL, NER_ENRICH_MAX_SNIPPETS, NER_ENRICH_MODEL_ID
- Skills: SKILLS_DYNAMIC_PATH
- Storage: USE_FIREBASE, FIREBASE_* (PROJECT_ID, CLIENT_EMAIL, PRIVATE_KEY, STORAGE_BUCKET)
- Embeddings: CHROMA_DIR
- Worker: REDIS_URL (used by Celery)
- Scraping: SCRAPER_ENGINE, USE_LINKEDIN_SCRAPE, LINKEDIN_EMAIL, LINKEDIN_PASSWORD (referenced in docs/endpoints; not hardcoded)

Frontend (`frontend`):
- REACT_APP_API_URL

Docker compose files propagate many of the above.

## Proposed `.env` (development) structure

- Database (local dev defaults are in docker-compose.yml; optional here)
- CORS
- LLM/Embeddings
- NLP/NER
- Storage
- Worker/Broker
- Frontend
- Debug/Diagnostics

See `.env.example` and `.env.production.example` for updated templates. Remove real secrets from `.env` before committing.

## Action items
- Removed hardcoded secrets from dev scripts.
- Updated Celery to respect REDIS_URL.
- Next: normalize `services/generation.py` duplicate definitions; add minimal type-safe env parsing where helpful.