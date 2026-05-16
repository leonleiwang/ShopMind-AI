# backend/app/tasks/celery_app.py
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "shopmind",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.ai_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)
