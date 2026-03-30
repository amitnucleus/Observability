import os
import time
import structlog
from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from app.models.job import Job
from app.kafka_client import publish

log = structlog.get_logger()

CELERY_BROKER_URL      = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND  = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
DATABASE_URL           = os.getenv("DATABASE_URL", "postgresql://pnog:pnog_secret@postgres:5432/pnog_db")

celery_app = Celery("pnog", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# Sync engine for Celery (Celery doesn't use asyncio)
sync_engine  = create_engine(DATABASE_URL)
SyncSession  = sessionmaker(sync_engine)

@celery_app.task(bind=True, max_retries=3, name="process_file")
def process_file(self, job_id: str, file_path: str):
    log.info("task_started", job_id=job_id, file_path=file_path)

    publish("pod.logs", {
        "event":   "task_started",
        "job_id":  job_id,
        "worker":  self.request.hostname,
        "layer":   "L2",
    })

    try:
        with SyncSession() as db:
            db.execute(update(Job).where(Job.id == job_id).values(status="processing"))
            db.commit()

        publish("db.queries", {
            "event":     "job_updated",
            "job_id":    job_id,
            "status":    "processing",
            "table":     "jobs",
            "operation": "UPDATE",
            "layer":     "L3",
        })

        # Simulate processing — read file, count lines, words
        start = time.time()
        with open(file_path, "rb") as f:
            content = f.read()

        lines  = content.count(b"\n")
        words  = len(content.split())
        size   = len(content)
        result = f"lines={lines} words={words} bytes={size}"
        elapsed = round(time.time() - start, 4)

        # Write result back to DB
        with SyncSession() as db:
            db.execute(
                update(Job).where(Job.id == job_id).values(status="done", result=result)
            )
            db.commit()

        publish("pod.logs", {
            "event":    "task_completed",
            "job_id":   job_id,
            "elapsed":  elapsed,
            "result":   result,
            "layer":    "L2",
        })

        publish("db.queries", {
            "event":     "job_updated",
            "job_id":    job_id,
            "status":    "done",
            "table":     "jobs",
            "operation": "UPDATE",
            "layer":     "L3",
        })

        log.info("task_completed", job_id=job_id, elapsed=elapsed)
        return result

    except Exception as exc:
        log.error("task_failed", job_id=job_id, error=str(exc))

        with SyncSession() as db:
            db.execute(update(Job).where(Job.id == job_id).values(status="failed"))
            db.commit()

        publish("pod.logs", {
            "event":  "task_failed",
            "job_id": job_id,
            "error":  str(exc),
            "layer":  "L2",
        })

        raise self.retry(exc=exc, countdown=5)
