# AWS Deployment Guide (ECS Fargate)

This guide provides a practical path to run this app on AWS with managed data services.

## Recommended AWS Architecture

- ECS Fargate service: `backend` container (FastAPI)
- ECS Fargate service: `web` container (Nginx + React static build)
- ECS Fargate service: `celery` worker container (optional but recommended)
- Amazon RDS PostgreSQL
- Amazon ElastiCache Redis
- Amazon EFS for persistent `uploaded_resumes` and `chroma_db`
- Application Load Balancer (ALB)

## 1) Prepare Environment Values

Start from [.env.production.example](.env.production.example) and set:

- `DATABASE_URL` (recommended for RDS)
- `REDIS_URL` (ElastiCache endpoint)
- `GOOGLE_API_KEY` (optional if using LLM features)
- `FRONTEND_ORIGIN` (your final domain)
- `APP_ENV=production`
- `SPACY_AUTO_DOWNLOAD=false`

Example:

```env
DATABASE_URL=postgresql://app_user:strong_password@my-rds-endpoint:5432/qualifyai
REDIS_URL=redis://my-redis-endpoint:6379/0
FRONTEND_ORIGIN=https://app.example.com
APP_ENV=production
SPACY_AUTO_DOWNLOAD=false
RUN_MIGRATIONS=false
UVICORN_WORKERS=2
```

Set `RUN_MIGRATIONS=true` only for a one-off migration task, not for all running replicas.

## 2) Build and Push Images to ECR

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

BACKEND_REPO=qualifyai-backend
FRONTEND_REPO=qualifyai-frontend

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Create repositories once
aws ecr create-repository --repository-name "$BACKEND_REPO" --region "$AWS_REGION" || true
aws ecr create-repository --repository-name "$FRONTEND_REPO" --region "$AWS_REGION" || true

# Build images
DOCKER_BUILDKIT=1 docker build -t "$BACKEND_REPO:latest" ./backend
DOCKER_BUILDKIT=1 docker build -t "$FRONTEND_REPO:latest" ./frontend

# Tag + push
BACKEND_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$BACKEND_REPO:latest"
FRONTEND_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$FRONTEND_REPO:latest"

docker tag "$BACKEND_REPO:latest" "$BACKEND_URI"
docker tag "$FRONTEND_REPO:latest" "$FRONTEND_URI"

docker push "$BACKEND_URI"
docker push "$FRONTEND_URI"
```

## 3) Create ECS Task Definitions

Create separate task definitions:

- `qualifyai-backend-task` (container port `8000`)
- `qualifyai-web-task` (container port `80`)
- `qualifyai-celery-task` (no external port)

Set environment variables in the task definitions, and put secrets in:

- AWS Systems Manager Parameter Store, or
- AWS Secrets Manager

Mount EFS into backend and celery tasks:

- `/app/uploaded_resumes`
- `/app/chroma_db`

## 4) Create ECS Services

- Backend service behind ALB target group `/api/*`
- Web service behind ALB target group `/*`
- Celery worker service without ALB

Health checks:

- Backend: `GET /api/v1/health`
- Web: `GET /`

## 5) Run Migrations Safely

Run one temporary ECS task with:

- same backend image
- `RUN_MIGRATIONS=true`

After migration completes, keep regular backend services with `RUN_MIGRATIONS=false`.

## 6) Validation Checklist

- `GET /api/v1/health` returns `ok: true`
- Frontend loads and API requests succeed through ALB
- Redis connectivity works for Celery
- EFS writes persist for uploaded resumes and vector DB

## Notes

- For production scale, prefer external managed vector storage if Chroma local storage growth becomes large.
- If you do not need async ingestion, you can skip deploying `celery`.
