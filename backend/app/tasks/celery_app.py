from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ontoforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.extraction_tasks"],
)
celery_app.conf.update(task_track_started=True, task_serializer="json", result_serializer="json", accept_content=["json"])
