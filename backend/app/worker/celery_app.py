from celery import Celery
import os

# Respect REDIS_URL when running in Docker or configured environments; fallback to local dev.
_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    'qualifyai',
    broker=_redis_url,
    backend=_redis_url,
)

celery_app.conf.task_routes = {
    'app.worker.tasks.processing_pipeline.process_applicant_pipeline': {'queue': 'default'},
}
