#!/usr/bin/env sh
set -e

# Default envs
: "${POSTGRES_USER:=postgres}"
: "${POSTGRES_PASSWORD:=12345678}"
: "${POSTGRES_DB:=qualifyai}"
: "${POSTGRES_SERVER:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${SPACY_MODEL:=en_core_web_sm}"
: "${SPACY_AUTO_DOWNLOAD:=false}"
: "${RUN_MIGRATIONS:=true}"
: "${UVICORN_WORKERS:=1}"
: "${UVICORN_TIMEOUT_KEEP_ALIVE:=30}"

export PYTHONPATH=/app

echo "[entrypoint] Waiting for database ${POSTGRES_SERVER}:${POSTGRES_PORT}..."
python - <<'PY'
import os, time, socket
host=os.getenv('POSTGRES_SERVER','postgres')
port=int(os.getenv('POSTGRES_PORT','5432'))
s=socket.socket(); s.settimeout(1)
for _ in range(60):
    try:
        s.connect((host, port)); s.close(); print('DB is up'); break
    except Exception:
        time.sleep(1)
else:
    print('DB not reachable, continuing anyway')
PY

# Run Alembic migrations if available
if [ "$RUN_MIGRATIONS" = "true" ] && [ -f "/app/alembic.ini" ]; then
  echo "[entrypoint] Running Alembic migrations..."
  alembic upgrade head || echo "[entrypoint] Alembic failed or no revisions; continuing"
fi

# Ensure spaCy model present (fallback)
if [ "$SPACY_AUTO_DOWNLOAD" = "true" ]; then
python - <<'PY'
import os
model=os.getenv('SPACY_MODEL','en_core_web_sm')
try:
    import spacy
    try:
        spacy.load(model)
    except Exception:
        from spacy.cli.download import download as dl
        print(f"[entrypoint] Downloading spaCy model {model}...")
        dl(model)
except Exception as e:
    print("[entrypoint] spaCy not available:", e)
PY
fi

# Start Uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS}" \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive "${UVICORN_TIMEOUT_KEEP_ALIVE}"
