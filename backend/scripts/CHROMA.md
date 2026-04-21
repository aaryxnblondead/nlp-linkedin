# Chroma configuration

- The vector store path is configured via `app.core.config.CHROMA_DIR`.
- Default: `backend/chroma_db` when running locally from the backend app root. You can override with `CHROMA_DIR` env var.
- All services and the preferred ingestion script (`ingest_resume_corpus.py`) use this config.

Note: The legacy `ingest_resumes_to_chromadb.py` still points to a hard-coded `chroma_db`; it is deprecated and will be removed after migration.
