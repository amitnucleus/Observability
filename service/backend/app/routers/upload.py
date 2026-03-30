import os
import uuid
import aiofiles
import structlog
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.job import Job
from app.kafka_client import publish

router = APIRouter()
log    = structlog.get_logger()

UPLOAD_DIR  = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    db:   AsyncSession = Depends(get_db),
):
    publish("app.events", {
        "event": "upload_received",
        "filename": file.filename,
        "cache_hit": False,
        "layer": "L1",
    })

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

    publish("app.events", {
        "event": "job_created",
        "job_id": job_id,
        "layer": "L1",
    })

    log.info("job_created", job_id=job_id, filename=file.filename)
    return {"job_id": job_id, "cached": False, "note": "Redis/Celery disabled; job not auto-processed"}


@router.get("/status/{job_id}")
async def job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job.status, "result": job.result}
