# Deployment Guide

For AWS ECS/Fargate deployment, see [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md).

This project ships with a production-ready Docker setup for:
- Postgres (database)
- Redis (Celery broker)
- Backend (FastAPI + Uvicorn)
- Celery Worker
- Frontend (React built and served via Nginx)

## Prerequisites
- Docker and Docker Compose v2 installed
- Ports available: 5432 (Postgres), 6379 (Redis), 8000 (Backend), 3000 (Frontend/Nginx)

## Configuration
- Database credentials default to local dev values (see `docker-compose.yml`). Change them for production.
- spaCy model preinstalled: `en_core_web_sm`. You can build with a different model via `--build-arg SPACY_MODEL=en_core_web_lg`.
- Frontend API URL: set at build with `--build-arg REACT_APP_API_URL=http://<backend-host>:8000/api/v1`.

## Build and Run

```sh
# Build images
docker compose build 

# Start the stack
docker compose up -d

# Check logs
docker compose logs -f backend
```

- Backend will run Alembic migrations automatically on container start (if `alembic.ini` and migrations exist).
- Backend exposes http://localhost:8000; Frontend at http://localhost:3000.

## One-time Tasks
- Create an admin user (if applicable) via your auth endpoint or a script.
- Load any seed data if needed.

## Environment Notes
- CORS is permissive in `backend/app/main.py` for development. Restrict in production.
- Uploaded resumes and ChromaDB data are persisted via named volumes `uploads` and `chromadb`.
- Celery worker processes asynchronous tasks. If not required, you can remove the `celery` service.
- You can provide `DATABASE_URL` (recommended for AWS RDS) instead of individual Postgres variables.
- Set `RUN_MIGRATIONS=false` for steady-state backend replicas and run migrations in a one-off task.

## Switching spaCy Model
To use a larger model:
```sh
docker compose build --build-arg SPACY_MODEL=en_core_web_lg backend celery
```

Or set `SPACY_MODEL` environment variable in the backend service if you already baked both models.

## Troubleshooting
- If the backend cannot reach Postgres, it will retry for up to ~60 seconds before continuing.
- To re-run migrations manually:
```sh
docker compose exec backend alembic upgrade head
```
- To inspect logs:
```sh
docker compose logs -f postgres redis backend celery frontend
```

## Security Hardening (Production)
- Replace default DB credentials and manage secrets through a secret manager or `.env` files not checked in.
- Restrict CORS origins.
- Ensure HTTPS termination at a reverse proxy/load balancer.
- Monitor with centralized logging and metrics.
