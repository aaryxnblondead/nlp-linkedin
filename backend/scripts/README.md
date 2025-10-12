# Scripts

Preferred ingestion script: `ingest_resume_corpus.py`

- Why: robust parsing, batching, metadata (source paths), and uses the shared CHROMA_DIR via backend config.
- Run from the `backend` folder for correct relative paths and environment resolution.

Deprecated legacy script: `ingest_resumes_to_chromadb.py`

- Kept temporarily for backward compatibility.
- Uses a hard-coded `chroma_db` path and a local embedding wrapper.
- Prefer switching to `ingest_resume_corpus.py`.
