from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.job import Job

router = APIRouter()

@router.get("/")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(50))
    jobs = result.scalars().all()
    return [{"job_id": str(j.id), "filename": j.filename, "status": j.status, "created_at": j.created_at} for j in jobs]

@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": str(job.id), "filename": job.filename, "status": job.status, "result": job.result}
