import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import upload, jobs, health
from app.routers.config import git as config_git
from app.database import engine, Base
from app.models.ast_graph import AstGraph, AstGraphIndividual  # noqa: F401 — register tables
from app.models.git_config import GitConfigRow  # noqa: F401 — register table with Base

log = structlog.get_logger()

app = FastAPI(title="PNOG Demo Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(jobs.router,   prefix="/jobs",   tags=["jobs"])
app.include_router(config_git.router, prefix="/git", tags=["git"])

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("pnog_service_started")
