import os
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

import httpx
from confluent_kafka import Consumer, TopicPartition
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.kafka_client import publish


router = APIRouter()


DEFAULT_REPO = os.getenv("GIT_REPO", "pnog/demo-service")
DEFAULT_REF = os.getenv("GIT_REF", "refs/heads/main")
DEFAULT_COMMIT = os.getenv("GIT_COMMIT", "abc123")

GIT_TOPIC = os.getenv("GIT_RELEASES_TOPIC", "git.releases")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

_config_lock = Lock()
_git_config = {
    "repo": DEFAULT_REPO,
    "ref": DEFAULT_REF,
    "commit": DEFAULT_COMMIT,
    "compare": "",
}


class GitConfig(BaseModel):
    repo: str = Field(..., description="GitHub repo in 'owner/repo' or URL form")
    ref: str = Field(..., description="Branch ref, e.g. 'main' or 'refs/heads/main'")
    commit: Optional[str] = Field(None, description="Optional commit SHA for simulation/demo")
    compare: Optional[str] = Field("", description="Optional compare field (demo)")


def _normalize_ref(ref: str) -> str:
    if ref.startswith("refs/heads/"):
        return ref
    return f"refs/heads/{ref}"


def _parse_github_repo(repo: str) -> Optional[tuple[str, str]]:
    # Accept:
    # - owner/repo
    # - https://github.com/owner/repo
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
    # Strip possible extra path fragments
    name = name.split("/")[0]
    return owner, name


def _read_latest_from_kafka(topic: str) -> Optional[dict[str, Any]]:
    # Single-partition assumption is fine for the demo stack (kafka-init creates 1 partition).
    # If your Kafka topic uses multiple partitions, we can enhance this later.
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
        # Seek to last available offset.
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

    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{owner}/{name}/commits/{branch}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
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
def get_git_config() -> GitConfig:
    with _config_lock:
        return GitConfig(
            repo=_git_config["repo"],
            ref=_git_config["ref"],
            commit=_git_config.get("commit"),
            compare=_git_config.get("compare", ""),
        )


@router.post("/config/")
@router.post("/config")
async def set_git_config(cfg: GitConfig) -> dict[str, Any]:
    with _config_lock:
        _git_config["repo"] = cfg.repo
        _git_config["ref"] = _normalize_ref(cfg.ref)
        _git_config["commit"] = cfg.commit or _git_config.get("commit") or DEFAULT_COMMIT
        _git_config["compare"] = cfg.compare or ""
    return {"status": "updated", "config": cfg.model_dump()}


@router.post("/simulate/")
@router.post("/simulate")
async def simulate_git_release(cfg: Optional[GitConfig] = None) -> dict[str, Any]:
    # Publishes to the same Kafka topic that the `git-webhook` service writes to.
    if cfg is None:
        cfg = get_git_config()

    payload = {
        "event": "push",
        "ref": _normalize_ref(cfg.ref),
        "commit": cfg.commit or DEFAULT_COMMIT,
        "pusher": "ui-simulator",
        "repo": cfg.repo,
        "compare": cfg.compare or "",
        "layer": "L5",
    }
    publish(GIT_TOPIC, payload)
    return {"status": "simulated", "topic": GIT_TOPIC, "payload": payload}


@router.get("/latest/")
@router.get("/latest")
async def get_latest_git_event() -> dict[str, Any]:
    # 1) Try Kafka (preferred: it represents real webhook-ingested git events)
    kafka_latest = await run_in_threadpool(_read_latest_from_kafka, GIT_TOPIC)
    if kafka_latest is not None:
        return {"source": "kafka", "event": kafka_latest}

    # 2) Fallback: fetch from GitHub API using current config.
    with _config_lock:
        cfg = GitConfig(
            repo=_git_config["repo"],
            ref=_git_config["ref"],
            commit=_git_config.get("commit"),
            compare=_git_config.get("compare", ""),
        )
    github_latest = await _fetch_latest_from_github(cfg)
    return {"source": "github_api", "event": github_latest}

