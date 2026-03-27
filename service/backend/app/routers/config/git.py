import os
import json
import io
import re
import ast
import zipfile
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.kafka_client import publish
from app.models.ast_graph import AstGraph, AstGraphIndividual
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


class AstGenerateRequest(BaseModel):
    repo: str = Field(..., description="GitHub repo in 'owner/repo' or URL form")
    ref: str = Field(..., description="Branch ref, e.g. 'main' or 'refs/heads/main'")
    github_token: Optional[str] = Field(None, description="Optional token override")


class AstSaveRequest(BaseModel):
    repo: str
    ref: str
    scanned_files: int = 0
    parsed_files: int = 0
    graph: dict[str, Any]


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


def _normalize_repo_display(repo: str) -> str:
    parsed = _parse_github_repo(repo)
    if not parsed:
        return repo.strip()
    return f"{parsed[0]}/{parsed[1]}"


def _strip_top_archive_prefix(path: str) -> str:
    parts = path.split("/", 1)
    if len(parts) == 2:
        return parts[1]
    return path


def _extract_symbols_for_python(source: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source)
    except Exception:
        return nodes

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(
                {
                    "kind": "function",
                    "name": node.name,
                    "line": getattr(node, "lineno", 0),
                }
            )
        elif isinstance(node, ast.ClassDef):
            nodes.append(
                {
                    "kind": "class",
                    "name": node.name,
                    "line": getattr(node, "lineno", 0),
                }
            )
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    nodes.append(
                        {
                            "kind": "variable",
                            "name": t.id,
                            "line": getattr(node, "lineno", 0),
                        }
                    )
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                nodes.append(
                    {
                        "kind": "variable",
                        "name": node.target.id,
                        "line": getattr(node, "lineno", 0),
                    }
                )
        elif isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name:
                nodes.append(
                    {
                        "kind": "call",
                        "name": func_name,
                        "line": getattr(node, "lineno", 0),
                    }
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                nodes.append({"kind": "import", "name": mod, "line": getattr(node, "lineno", 0)})
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod:
                nodes.append({"kind": "import", "name": mod, "line": getattr(node, "lineno", 0)})
    return nodes


JS_SYMBOL_RE = re.compile(r"(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
JS_CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)")
JS_IMPORT_RE = re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]")
JS_COMPONENT_RE = re.compile(r"(?:export\s+default\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(")
JS_VARIABLE_RE = re.compile(r"(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=")
JS_CALL_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_\.]*)\s*\(")


def _extract_symbols_for_js(source: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        raw = line
        line = line.strip()
        if not line or line.startswith("//"):
            continue

        comp_match = JS_COMPONENT_RE.search(line)
        if comp_match:
            nodes.append({"kind": "component", "name": comp_match.group(1), "line": i})

        fn_match = JS_SYMBOL_RE.search(line)
        if fn_match:
            nodes.append({"kind": "function", "name": fn_match.group(1), "line": i})
        cls_match = JS_CLASS_RE.search(line)
        if cls_match:
            nodes.append({"kind": "class", "name": cls_match.group(1), "line": i})
        imp_match = JS_IMPORT_RE.search(line)
        if imp_match:
            mod = imp_match.group(1)
            nodes.append({"kind": "import", "name": mod, "line": i})
        var_match = JS_VARIABLE_RE.search(line)
        if var_match:
            nodes.append({"kind": "variable", "name": var_match.group(1), "line": i})

        # Capture call expressions like useState(...), fetch(...), api.do(...)
        for m in JS_CALL_RE.finditer(raw):
            callee = m.group(1)
            if callee in {"if", "for", "while", "switch", "catch", "function"}:
                continue
            nodes.append({"kind": "call", "name": callee, "line": i})
    return nodes


async def _download_repo_archive(owner: str, name: str, branch: str, token: str) -> bytes:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{owner}/{name}/zipball/{quote(branch, safe='')}"
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            if r.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"GitHub 404: unable to download archive for {owner}/{name}@{branch}. Check repo, branch, and token access.",
                )
            if r.status_code in (401, 403):
                raise HTTPException(
                    status_code=r.status_code,
                    detail="GitHub auth/rate-limit error while downloading repo archive. Check token permissions.",
                )
            raise HTTPException(status_code=502, detail=f"GitHub archive API error: {r.status_code} {r.text}")
        return r.content


async def _build_ast_graph_from_repo(cfg: GitConfig) -> dict[str, Any]:
    parsed = _parse_github_repo(cfg.repo)
    if not parsed:
        raise HTTPException(status_code=400, detail="repo must be 'owner/repo' or a GitHub URL")
    owner, name = parsed
    ref = _normalize_ref(cfg.ref)
    branch = ref[len("refs/heads/") :]
    token = (cfg.github_token or "").strip() or _env_token()

    archive_bytes = await _download_repo_archive(owner, name, branch, token)
    zf = zipfile.ZipFile(io.BytesIO(archive_bytes))

    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []
    per_file_graphs: list[dict[str, Any]] = []
    import_nodes_seen: set[str] = set()
    max_nodes = 6000

    scanned_files = 0
    parsed_files = 0

    for info in zf.infolist():
        if info.is_dir():
            continue
        rel_path = _strip_top_archive_prefix(info.filename)
        lower = rel_path.lower()
        if "/node_modules/" in lower or "/.git/" in lower or "/dist/" in lower or "/build/" in lower:
            continue
        ext = os.path.splitext(lower)[1]
        if ext not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            continue

        scanned_files += 1
        try:
            source = zf.read(info).decode("utf-8", errors="replace")
        except Exception:
            continue

        file_node_id = f"file:{rel_path}"
        graph_nodes.append({"id": file_node_id, "type": "file", "label": rel_path})
        file_graph_nodes: list[dict[str, Any]] = [{"id": file_node_id, "type": "file", "label": rel_path}]
        file_graph_edges: list[dict[str, Any]] = []

        if ext == ".py":
            sym_nodes = _extract_symbols_for_python(source)
        else:
            sym_nodes = _extract_symbols_for_js(source)

        parsed_files += 1
        for sym in sym_nodes:
            if len(graph_nodes) >= max_nodes:
                break
            if sym["kind"] == "import":
                import_id = f"import:{sym['name']}"
                if import_id not in import_nodes_seen:
                    import_nodes_seen.add(import_id)
                    graph_nodes.append({"id": import_id, "type": "import", "label": sym["name"]})
                graph_edges.append({"source": file_node_id, "target": import_id, "relation": "imports"})
                file_graph_nodes.append({"id": import_id, "type": "import", "label": sym["name"]})
                file_graph_edges.append({"source": file_node_id, "target": import_id, "relation": "imports"})
                continue
            sym_id = f"symbol:{rel_path}:{sym['name']}:{sym['line']}"
            symbol_node = {
                "id": sym_id,
                "type": sym["kind"],
                "label": sym["name"],
                "file": rel_path,
                "line": sym["line"],
            }
            graph_nodes.append(symbol_node)
            file_graph_nodes.append(symbol_node)
            graph_edges.append({"source": file_node_id, "target": sym_id, "relation": "contains"})
            file_graph_edges.append({"source": file_node_id, "target": sym_id, "relation": "contains"})

        per_file_graphs.append(
            {
                "file_path": rel_path,
                "nodes": file_graph_nodes,
                "edges": file_graph_edges,
            }
        )
        if len(graph_nodes) >= max_nodes:
            break

    return {
        "repo": f"{owner}/{name}",
        "ref": ref,
        "scanned_files": scanned_files,
        "parsed_files": parsed_files,
        "nodes": graph_nodes,
        "edges": graph_edges,
        "individual_graphs": per_file_graphs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _persist_ast_graph(db: AsyncSession, graph: dict[str, Any]) -> tuple[str, int]:
    consolidated = {"nodes": graph["nodes"], "edges": graph["edges"]}
    row = AstGraph(
        repo=graph["repo"],
        ref=graph["ref"],
        scanned_files=graph["scanned_files"],
        parsed_files=graph["parsed_files"],
        node_count=len(graph["nodes"]),
        edge_count=len(graph["edges"]),
        consolidated_graph=consolidated,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.flush()

    individual_rows = []
    for item in graph.get("individual_graphs", []):
        individual_rows.append(
            AstGraphIndividual(
                ast_graph_id=row.id,
                file_path=item["file_path"],
                node_count=len(item.get("nodes", [])),
                edge_count=len(item.get("edges", [])),
                graph={"nodes": item.get("nodes", []), "edges": item.get("edges", [])},
                created_at=datetime.utcnow(),
            )
        )
    if individual_rows:
        db.add_all(individual_rows)

    await db.commit()
    return str(row.id), len(individual_rows)


def _build_individual_graphs_from_consolidated(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])

    file_nodes = [n for n in nodes if n.get("type") == "file" and str(n.get("id", "")).startswith("file:")]
    file_node_by_id = {n["id"]: n for n in file_nodes if "id" in n}

    per_file: dict[str, dict[str, Any]] = {}
    for file_id, file_node in file_node_by_id.items():
        path = str(file_node.get("label") or file_id.removeprefix("file:"))
        per_file[path] = {"file_path": path, "nodes": [file_node], "edges": []}

    node_by_id = {n.get("id"): n for n in nodes if n.get("id")}

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        if str(source).startswith("file:"):
            file_node = file_node_by_id.get(str(source))
            if file_node is None:
                continue
            path = str(file_node.get("label") or str(source).removeprefix("file:"))
            bucket = per_file.setdefault(path, {"file_path": path, "nodes": [file_node], "edges": []})
            bucket["edges"].append(edge)
            target_node = node_by_id.get(target)
            if target_node is not None:
                bucket["nodes"].append(target_node)

    # De-duplicate per-file node ids
    result: list[dict[str, Any]] = []
    for item in per_file.values():
        dedup: dict[str, dict[str, Any]] = {}
        for node in item["nodes"]:
            node_id = str(node.get("id") or "")
            if node_id:
                dedup[node_id] = node
        result.append({"file_path": item["file_path"], "nodes": list(dedup.values()), "edges": item["edges"]})
    return result


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

    # Branch names with slashes must be URL-encoded (e.g. feature/foo → feature%2Ffoo).
    url = f"https://api.github.com/repos/{owner}/{name}/commits/{quote(branch, safe='')}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            if r.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"GitHub 404: no branch named '{branch}' in {owner}/{name}, or repo is private / URL wrong. "
                        "Ref / branch must be a real Git branch (e.g. main, master), not a folder path inside the repo."
                    ),
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


@router.post("/ast/generate/")
@router.post("/ast/generate")
async def generate_ast_graph(
    req: Optional[AstGenerateRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if req is None:
        cfg = await load_effective_git_config(db)
    else:
        merged = await merge_git_config_with_stored(
            GitConfig(repo=req.repo, ref=req.ref, github_token=req.github_token),
            db,
        )
        cfg = GitConfig(
            repo=_normalize_repo_display(merged.repo),
            ref=_normalize_ref(merged.ref),
            github_token=merged.github_token,
        )

    graph = await _build_ast_graph_from_repo(cfg)
    return {
        "ok": True,
        "message": "AST graph generated.",
        "repo": graph["repo"],
        "ref": graph["ref"],
        "scanned_files": graph["scanned_files"],
        "parsed_files": graph["parsed_files"],
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "generated_at": graph["generated_at"],
        "graph": {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
    }


@router.post("/ast/save/")
@router.post("/ast/save")
async def save_ast_graph(req: AstSaveRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    nodes = list((req.graph or {}).get("nodes") or [])
    edges = list((req.graph or {}).get("edges") or [])
    if not nodes and not edges:
        raise HTTPException(status_code=400, detail="graph.nodes or graph.edges is required")

    row = AstGraph(
        repo=_normalize_repo_display(req.repo),
        ref=_normalize_ref(req.ref),
        scanned_files=max(0, int(req.scanned_files)),
        parsed_files=max(0, int(req.parsed_files)),
        node_count=len(nodes),
        edge_count=len(edges),
        consolidated_graph={"nodes": nodes, "edges": edges},
        created_at=datetime.utcnow(),
    )
    db.add(row)
    await db.flush()

    per_file_graphs = _build_individual_graphs_from_consolidated({"nodes": nodes, "edges": edges})
    ind_rows = [
        AstGraphIndividual(
            ast_graph_id=row.id,
            file_path=item["file_path"],
            node_count=len(item.get("nodes") or []),
            edge_count=len(item.get("edges") or []),
            graph={"nodes": item.get("nodes") or [], "edges": item.get("edges") or []},
            created_at=datetime.utcnow(),
        )
        for item in per_file_graphs
    ]
    if ind_rows:
        db.add_all(ind_rows)

    await db.commit()
    return {
        "ok": True,
        "message": "AST graph saved to database.",
        "ast_graph_id": str(row.id),
        "individual_graphs_saved": len(ind_rows),
    }


@router.get("/ast/list/")
@router.get("/ast/list")
async def list_saved_ast_graphs(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    rows = (
        await db.execute(select(AstGraph).order_by(desc(AstGraph.created_at)).limit(50))
    ).scalars().all()

    ast_ids = [r.id for r in rows]
    count_by_ast_id: dict[str, int] = {}
    if ast_ids:
        ind_rows = (
            await db.execute(
                select(AstGraphIndividual.ast_graph_id).where(AstGraphIndividual.ast_graph_id.in_(ast_ids))
            )
        ).scalars().all()
        for ast_id in ind_rows:
            key = str(ast_id)
            count_by_ast_id[key] = count_by_ast_id.get(key, 0) + 1

    items = [
        {
            "id": str(r.id),
            "repo": r.repo,
            "ref": r.ref,
            "scanned_files": r.scanned_files,
            "parsed_files": r.parsed_files,
            "node_count": r.node_count,
            "edge_count": r.edge_count,
            "individual_graphs_count": count_by_ast_id.get(str(r.id), 0),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"ok": True, "items": items}


@router.get("/ast/{ast_graph_id}/")
@router.get("/ast/{ast_graph_id}")
async def get_saved_ast_graph(ast_graph_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = (
        await db.execute(select(AstGraph).where(AstGraph.id == ast_graph_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="AST graph not found")

    individual_rows = (
        await db.execute(
            select(AstGraphIndividual).where(AstGraphIndividual.ast_graph_id == row.id).order_by(AstGraphIndividual.file_path)
        )
    ).scalars().all()

    return {
        "ok": True,
        "item": {
            "id": str(row.id),
            "repo": row.repo,
            "ref": row.ref,
            "scanned_files": row.scanned_files,
            "parsed_files": row.parsed_files,
            "node_count": row.node_count,
            "edge_count": row.edge_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "graph": row.consolidated_graph or {"nodes": [], "edges": []},
            "individual_graphs": [
                {
                    "id": str(r.id),
                    "file_path": r.file_path,
                    "node_count": r.node_count,
                    "edge_count": r.edge_count,
                }
                for r in individual_rows
            ],
        },
    }


@router.get("/ast/individual/{individual_graph_id}/")
@router.get("/ast/individual/{individual_graph_id}")
async def get_saved_individual_ast_graph(individual_graph_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = (
        await db.execute(select(AstGraphIndividual).where(AstGraphIndividual.id == individual_graph_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Individual AST graph not found")

    parent = (
        await db.execute(select(AstGraph).where(AstGraph.id == row.ast_graph_id))
    ).scalar_one_or_none()

    return {
        "ok": True,
        "item": {
            "id": str(row.id),
            "ast_graph_id": str(row.ast_graph_id),
            "repo": parent.repo if parent else None,
            "ref": parent.ref if parent else None,
            "file_path": row.file_path,
            "node_count": row.node_count,
            "edge_count": row.edge_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "graph": row.graph or {"nodes": [], "edges": []},
        },
    }
