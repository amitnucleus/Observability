import os
import uuid
import aiofiles
import structlog
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database import get_db
from app.models.job import Job
from app.kafka_client import publish
from app.tasks.process import process_file

router = APIRouter()
log    = structlog.get_logger()

REDIS_URL   = os.getenv("REDIS_URL", "redis://redis:6379/0")
UPLOAD_DIR  = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def get_redis():
    r = aioredis.from_url(REDIS_URL)
    try:
        yield r
    finally:
        await r.close()

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    db:   AsyncSession = Depends(get_db),
    r:    aioredis.Redis = Depends(get_redis),
):
    # L4 Cache — check if this filename was recently processed
    cache_key = f"upload:{file.filename}"
    cached = await r.get(cache_key)

    publish("app.events", {
        "event": "upload_received",
        "filename": file.filename,
        "cache_hit": bool(cached),
        "layer": "L1",
    })

    if cached:
        log.info("cache_hit", filename=file.filename)
        return {"job_id": cached.decode(), "cached": True}

    # Save file
    job_id  = str(uuid.uuid4())
    path    = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    content = await file.read()

    async with aiofiles.open(path, "wb") as f:
        await f.write(content)

    # L3 DB — write job record
    job = Job(id=job_id, filename=file.filename, status="pending", file_size=len(content))
    db.add(job)
    await db.commit()

    publish("db.queries", {
        "event": "job_created",
        "job_id": job_id,
        "table": "jobs",
        "operation": "INSERT",
        "layer": "L3",
    })

    # L4 Cache — store result for 60s
    await r.setex(cache_key, 60, job_id)

    # Dispatch to Celery worker (L2 Pod)
    process_file.delay(job_id, path)

    publish("app.events", {
        "event": "job_dispatched",
        "job_id": job_id,
        "layer": "L1",
    })

    log.info("job_created", job_id=job_id, filename=file.filename)
    return {"job_id": job_id, "cached": False}


@router.get("/status/{job_id}")
async def job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job.status, "result": job.result}
