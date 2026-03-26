import os
import json
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.kafka_client import publish
from app.models.git_config import GitConfigRow, SINGLETON_ID

router = APIRouter()

DEFAULT_REPO = os.getenv("GIT_REPO", "pnog/demo-service")
DEFAULT_REF = os.getenv("GIT_REF", "refs/heads/main")
DEFAULT_COMMIT = os.getenv("GIT_COMMIT", "abc123")

GIT_TOPIC = os.getenv("GIT_RELEASES_TOPIC", "git.releases")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "").strip()
DISABLE_KAFKA = os.getenv("DISABLE_KAFKA", "").strip().lower() in ("1", "true", "yes", "on")


class GitConfig(BaseModel):
    repo: str = Field(..., description="GitHub repo in 'owner/repo' or URL form")
    ref: str = Field(..., description="Branch ref, e.g. 'main' or 'refs/heads/main'")
    github_token: Optional[str] = Field(None, description="Optional GitHub token for private repos / higher rate limits")


class GitConfigPublic(BaseModel):
    repo: str
    ref: str
    github_token_present: bool = False


def _normalize_ref(ref: str) -> str:
    if ref.startswith("refs/heads/"):
        return ref
    return f"refs/heads/{ref}"


def _env_token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()


async def _load_row(db: AsyncSession) -> Optional[GitConfigRow]:
    result = await db.execute(select(GitConfigRow).where(GitConfigRow.id == SINGLETON_ID))
    return result.scalar_one_or_none()


async def load_effective_git_config(db: AsyncSession) -> GitConfig:
    row = await _load_row(db)
    if row is None:
        return GitConfig(
            repo=DEFAULT_REPO,
            ref=_normalize_ref(DEFAULT_REF),
            github_token=_env_token() or None,
        )
    token = (row.github_token or "").strip() or None
    if not token:
        token = _env_token() or None
    return GitConfig(repo=row.repo, ref=row.ref, github_token=token)


async def merge_git_config_with_stored(cfg: GitConfig, db: AsyncSession) -> GitConfig:
    """Use request repo/ref; if token is empty, use token from DB (or env)."""
    token = (cfg.github_token or "").strip()
    if token:
        return GitConfig(repo=cfg.repo.strip(), ref=cfg.ref, github_token=token)
    stored = await load_effective_git_config(db)
    return GitConfig(
        repo=cfg.repo.strip(),
        ref=cfg.ref,
        github_token=(stored.github_token or "").strip() or None,
    )


def _public_from_row(row: GitConfigRow) -> GitConfigPublic:
    token = (row.github_token or "").strip()
    return GitConfigPublic(
        repo=row.repo,
        ref=row.ref,
        github_token_present=bool(token),
    )


async def _public_config(db: AsyncSession) -> GitConfigPublic:
    row = await _load_row(db)
    if row is None:
        return GitConfigPublic(
            repo=DEFAULT_REPO,
            ref=_normalize_ref(DEFAULT_REF),
            github_token_present=bool(_env_token()),
        )
    return _public_from_row(row)


def _parse_github_repo(repo: str) -> Optional[tuple[str, str]]:
    repo = repo.strip()
    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/") :]
    elif repo.startswith("http://github.com/"):
        repo = repo[len("http://github.com/") :]

    if "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    if not owner or not name:
        return None
    name = name.split("/")[0]
    return owner, name


def _read_latest_from_kafka(topic: str) -> Optional[dict[str, Any]]:
    if DISABLE_KAFKA or not KAFKA_BROKER:
        return None

    try:
        from confluent_kafka import Consumer, TopicPartition  # type: ignore
    except Exception:
        return None

    c = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": f"git-dashboard-{os.getpid()}",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )

    try:
        tp = TopicPartition(topic, 0)
        c.assign([tp])
        low, high = c.get_watermark_offsets(tp, timeout=5)
        if high <= 0:
            return None
        last_offset = high - 1
        c.seek(TopicPartition(topic, 0, last_offset))
        msg = c.poll(2.0)
        if msg is None or msg.value() is None:
            return None
        raw = msg.value().decode("utf-8")
        return json.loads(raw)
    finally:
        try:
            c.close()
        except Exception:
            pass


async def _fetch_latest_from_github(cfg: GitConfig) -> dict[str, Any]:
    parsed = _parse_github_repo(cfg.repo)
    if not parsed:
        raise HTTPException(status_code=400, detail="repo must be 'owner/repo' or a GitHub URL")
    owner, name = parsed

    ref = _normalize_ref(cfg.ref)
    branch = ref[len("refs/heads/") :]

    token = (cfg.github_token or "").strip()
    if not token:
        token = _env_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{name}/commits/{branch}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            if r.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="GitHub 404: repo or branch not found (or repo is private without token)",
                )
            if r.status_code in (401, 403):
                raise HTTPException(
                    status_code=r.status_code,
                    detail="GitHub auth/rate-limit error: add a GitHub token or check permissions",
                )
            raise HTTPException(status_code=502, detail=f"GitHub API error: {r.status_code} {r.text}")
        data = r.json()

    sha = data.get("sha", "")
    commit = data.get("commit", {}) or {}
    message = commit.get("message", "")
    now = datetime.now(timezone.utc).isoformat()

    return {
        "source": "github_api",
        "event": "git_commit_snapshot",
        "repo": f"{owner}/{name}",
        "ref": ref,
        "commit": sha,
        "message": message,
        "timestamp": now,
        "layer": "L5",
    }


@router.get("/config/")
@router.get("/config")
async def get_git_config(db: AsyncSession = Depends(get_db)) -> GitConfigPublic:
    return await _public_config(db)


@router.post("/config/")
@router.post("/config")
async def set_git_config(cfg: GitConfig, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    ref_norm = _normalize_ref(cfg.ref)
    row = await _load_row(db)
    now = datetime.utcnow()

    if row is None:
        row = GitConfigRow(
            id=SINGLETON_ID,
            repo=cfg.repo.strip(),
            ref=ref_norm,
            github_token=None,
            updated_at=now,
        )
        if cfg.github_token is not None and cfg.github_token.strip() != "":
            row.github_token = cfg.github_token.strip()
        db.add(row)
    else:
        row.repo = cfg.repo.strip()
        row.ref = ref_norm
        if cfg.github_token is not None and cfg.github_token.strip() != "":
            row.github_token = cfg.github_token.strip()
        row.updated_at = now

    await db.commit()
    await db.refresh(row)
    return {"status": "updated", "config": _public_from_row(row).model_dump()}


@router.post("/simulate/")
@router.post("/simulate")
async def simulate_git_release(
    cfg: Optional[GitConfig] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if cfg is None:
        cfg = await load_effective_git_config(db)

    payload = {
        "event": "push",
        "ref": _normalize_ref(cfg.ref),
        "commit": DEFAULT_COMMIT,
        "pusher": "ui-simulator",
        "repo": cfg.repo,
        "compare": "",
        "layer": "L5",
    }
    publish(GIT_TOPIC, payload)
    return {"status": "simulated", "topic": GIT_TOPIC, "payload": payload}


@router.post("/connectivity/")
@router.post("/connectivity")
async def check_git_connectivity(
    cfg: Optional[GitConfig] = Body(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if cfg is None:
        effective = await load_effective_git_config(db)
    else:
        effective = await merge_git_config_with_stored(cfg, db)
    try:
        data = await _fetch_latest_from_github(effective)
        sha = str(data.get("commit") or "")
        msg = str(data.get("message") or "")
        return {
            "ok": True,
            "message": "GitHub reachable; branch resolves to a commit.",
            "repo": data.get("repo"),
            "ref": data.get("ref"),
            "commit_sha": sha[:40],
            "commit_message_preview": msg[:200].replace("\n", " "),
        }
    except HTTPException as e:
        detail = e.detail
        if not isinstance(detail, str):
            detail = str(detail)
        return {
            "ok": False,
            "message": detail,
            "status_code": e.status_code,
        }


@router.get("/latest/")
@router.get("/latest")
async def get_latest_git_event(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    kafka_latest = await run_in_threadpool(_read_latest_from_kafka, GIT_TOPIC)
    if kafka_latest is not None:
        return {"source": "kafka", "event": kafka_latest}

    cfg = await load_effective_git_config(db)
    github_latest = await _fetch_latest_from_github(cfg)
    return {"source": "github_api", "event": github_latest}
