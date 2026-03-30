import { Fragment, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function Home() {
  const [gitRepo, setGitRepo] = useState("");
  const [gitRef, setGitRef] = useState("main");
  const [astLoading, setAstLoading] = useState(false);
  const [astSaving, setAstSaving] = useState(false);
  const [astMsg, setAstMsg] = useState("");
  const [astStats, setAstStats] = useState(null);
  const [savedGraphs, setSavedGraphs] = useState([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [viewingGraphId, setViewingGraphId] = useState(null);
  const [viewGraphOpen, setViewGraphOpen] = useState(false);
  const [viewGraphLoading, setViewGraphLoading] = useState(false);
  const [viewGraphError, setViewGraphError] = useState("");
  const [viewGraphData, setViewGraphData] = useState(null);
  const [graphScale, setGraphScale] = useState(1);
  const [graphPan, setGraphPan] = useState({ x: 0, y: 0 });
  const [isGraphPanning, setIsGraphPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [expandedSavedGraphId, setExpandedSavedGraphId] = useState(null);
  const [expandedIndividuals, setExpandedIndividuals] = useState([]);
  const [expandedLoading, setExpandedLoading] = useState(false);
  const [expandedError, setExpandedError] = useState("");

  async function loadGitDefaults() {
    try {
      const res = await fetch(`${API}/git/config/`);
      if (!res.ok) return;
      const cfg = await res.json();
      setGitRepo(cfg.repo || "");
      setGitRef((cfg.ref || "refs/heads/main").replace("refs/heads/", ""));
    } catch (_e) {
      // non-blocking on home page
    }
  }

  async function generateAstGraph() {
    if (!gitRepo || !gitRef) {
      setAstMsg("Please enter both repo and branch.");
      return;
    }
    setAstLoading(true);
    setAstMsg("");
    setAstStats(null);
    try {
      const res = await fetch(`${API}/git/ast/generate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo: gitRepo, ref: gitRef }),
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.message || "Failed to generate AST graph");
      }
      setAstStats({
        repo: data.repo,
        ref: data.ref,
        scannedFiles: data.scanned_files,
        parsedFiles: data.parsed_files,
        nodeCount: data.node_count,
        edgeCount: data.edge_count,
        functionGraphCount: data.function_graph_count || 0,
        generatedAt: data.generated_at,
        graph: data.graph,
        functionGraphs: data.function_graphs || [],
      });
      setAstMsg("AST graph generated.");
    } catch (e) {
      setAstMsg(`AST generation failed: ${e.message}`);
    } finally {
      setAstLoading(false);
    }
  }

  async function saveAstGraphToDb() {
    if (!astStats?.graph) {
      setAstMsg("Generate AST graph first, then save.");
      return;
    }
    setAstSaving(true);
    setAstMsg("");
    try {
      const res = await fetch(`${API}/git/ast/save/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo: astStats.repo,
          ref: astStats.ref,
          scanned_files: astStats.scannedFiles,
          parsed_files: astStats.parsedFiles,
          graph: astStats.graph,
          function_graphs: astStats.functionGraphs || [],
        }),
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.message || "Failed to save AST graph");
      }
      setAstMsg(
        `Saved to DB. Graph ID: ${data.ast_graph_id} (${data.individual_graphs_saved} file graphs, ${data.function_graphs_saved || 0} function graphs).`
      );
      await loadSavedGraphs();
    } catch (e) {
      setAstMsg(`Save failed: ${e.message}`);
    } finally {
      setAstSaving(false);
    }
  }

  async function loadSavedGraphs() {
    setSavedLoading(true);
    try {
      const res = await fetch(`${API}/git/ast/list/`);
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.message || "Failed to load saved graphs");
      }
      setSavedGraphs(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      setAstMsg(`Could not load saved graphs: ${e.message}`);
    } finally {
      setSavedLoading(false);
    }
  }

  async function viewSavedGraph(graphId) {
    setViewingGraphId(graphId);
    setViewGraphOpen(true);
    setViewGraphLoading(true);
    setViewGraphError("");
    setViewGraphData(null);
    try {
      const res = await fetch(`${API}/git/ast/${graphId}/`);
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.detail || data.message || "Failed to load graph");
      }
      setGraphScale(1);
      setGraphPan({ x: 0, y: 0 });
      setSelectedNodeId(null);
      setViewGraphData(data.item);
    } catch (e) {
      setViewGraphError(e.message || "Could not load graph");
    } finally {
      setViewGraphLoading(false);
    }
  }

  function closeGraphModal() {
    setViewGraphOpen(false);
    setViewingGraphId(null);
    setIsGraphPanning(false);
  }

  function renderGraphPreview(graphObj) {
    const nodes = Array.isArray(graphObj?.nodes) ? graphObj.nodes : [];
    const edges = Array.isArray(graphObj?.edges) ? graphObj.edges : [];
    if (nodes.length === 0) return <p style={{ color: "#94a3b8", margin: 0 }}>No nodes in graph.</p>;

    const normalizedNodes = nodes.map((n, idx) => {
      const nodeId = n?.id ?? `node-${idx}`;
      const nodeType = n?.type || "node";
      const nodeLabel = n?.label || n?.name || String(nodeId);
      return { ...n, id: nodeId, type: nodeType, label: nodeLabel };
    });

    const displayNodes = normalizedNodes;
    const ids = new Set(displayNodes.map((n) => n.id));
    const displayEdges = edges.filter((e) => ids.has(e.source) && ids.has(e.target));

    const width = 920;
    const height = 520;

    const pos = {};
    const incoming = new Map();
    const outgoing = new Map();
    displayNodes.forEach((n) => {
      incoming.set(n.id, 0);
      outgoing.set(n.id, []);
    });
    displayEdges.forEach((e) => {
      if (!incoming.has(e.target)) return;
      incoming.set(e.target, (incoming.get(e.target) || 0) + 1);
      outgoing.get(e.source)?.push(e.target);
    });

    const roots = displayNodes.filter((n) => (incoming.get(n.id) || 0) === 0);
    const isTreeLike = roots.length > 0 && displayEdges.length >= Math.max(1, displayNodes.length - 1);

    if (isTreeLike) {
      const depthById = new Map();
      const queue = [];
      roots.forEach((r) => {
        depthById.set(r.id, 0);
        queue.push(r.id);
      });
      while (queue.length > 0) {
        const cur = queue.shift();
        const d = depthById.get(cur) || 0;
        for (const nxt of outgoing.get(cur) || []) {
          if (!depthById.has(nxt) || (depthById.get(nxt) || 0) > d + 1) {
            depthById.set(nxt, d + 1);
            queue.push(nxt);
          }
        }
      }
      const layers = new Map();
      displayNodes.forEach((n) => {
        const d = depthById.get(n.id) ?? 0;
        if (!layers.has(d)) layers.set(d, []);
        layers.get(d).push(n);
      });
      const maxDepth = Math.max(...layers.keys(), 0);
      const yGap = (height - 80) / Math.max(1, maxDepth + 1);
      for (const [d, layerNodes] of [...layers.entries()].sort((a, b) => a[0] - b[0])) {
        const xGap = width / (layerNodes.length + 1);
        layerNodes.forEach((n, idx) => {
          pos[n.id] = { x: xGap * (idx + 1), y: 40 + d * yGap };
        });
      }
    } else {
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) * 0.38;
      displayNodes.forEach((n, i) => {
        const a = (2 * Math.PI * i) / Math.max(1, displayNodes.length);
        pos[n.id] = {
          x: cx + radius * Math.cos(a),
          y: cy + radius * Math.sin(a),
        };
      });
    }

    const colorByType = {
      file: "#60a5fa",
      function: "#34d399",
      class: "#f59e0b",
      import: "#c084fc",
      default: "#94a3b8",
    };

    const selectedNode = displayNodes.find((n) => n.id === selectedNodeId) || null;

    function onWheel(e) {
      e.preventDefault();
      const direction = e.deltaY > 0 ? -0.1 : 0.1;
      setGraphScale((s) => Math.max(0.35, Math.min(4, s + direction)));
    }

    function onMouseDown(e) {
      setIsGraphPanning(true);
      setPanStart({ x: e.clientX - graphPan.x, y: e.clientY - graphPan.y });
    }

    function onMouseMove(e) {
      if (!isGraphPanning) return;
      setGraphPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    }

    function onMouseUp() {
      setIsGraphPanning(false);
    }

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <p style={{ margin: 0, fontSize: 11, color: "#94a3b8" }}>
          Showing all nodes and edges ({displayNodes.length} nodes, {displayEdges.length} edges). Scroll to zoom, drag to pan, click a node for details.
        </p>
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          onWheel={onWheel}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          style={{
            width: "100%",
            background: "#0b1220",
            borderRadius: 10,
            border: "1px solid #334155",
            cursor: isGraphPanning ? "grabbing" : "grab",
          }}
        >
          <g transform={`translate(${graphPan.x} ${graphPan.y}) scale(${graphScale})`}>
            {displayEdges.map((e, idx) => {
              const s = pos[e.source];
              const t = pos[e.target];
              if (!s || !t) return null;
              return (
                <g key={`e-${idx}`}>
                  <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#334155" strokeWidth="1.2" />
                  {e.relation ? (
                    <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4} fill="#64748b" fontSize="10" textAnchor="middle">
                      {e.relation}
                    </text>
                  ) : null}
                </g>
              );
            })}
            {displayNodes.map((n) => {
              const p = pos[n.id];
              const c = colorByType[n.type] || colorByType.default;
              const isSelected = selectedNodeId === n.id;
              return (
                <g key={n.id} onClick={(e) => { e.stopPropagation(); setSelectedNodeId(n.id); }}>
                  <circle cx={p.x} cy={p.y} r={isSelected ? "8" : "6"} fill={c} stroke={isSelected ? "#f8fafc" : "none"} strokeWidth="2" />
                  <title>{`${n.type || "node"}: ${n.label || n.id}`}</title>
                </g>
              );
            })}
          </g>
        </svg>
        {selectedNode ? (
          <p style={{ margin: 0, fontSize: 12, color: "#cbd5e1", wordBreak: "break-all" }}>
            Selected: <strong>{selectedNode.type || "node"}</strong> — {selectedNode.label || selectedNode.id}
          </p>
        ) : null}
        <div style={{ border: "1px solid #334155", borderRadius: 10, background: "#0b1220", padding: 10 }}>
          <p style={{ margin: "0 0 8px", color: "#94a3b8", fontSize: 12, fontWeight: 700 }}>
            Node details ({displayNodes.length})
          </p>
          <div style={{ maxHeight: 180, overflow: "auto", fontSize: 12 }}>
            {displayNodes.map((n) => (
              <div
                key={`node-row-${n.id}`}
                onClick={() => setSelectedNodeId(n.id)}
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #1e293b",
                  cursor: "pointer",
                  background: selectedNodeId === n.id ? "#1e293b" : "transparent",
                  color: "#cbd5e1",
                }}
              >
                <span style={{ color: "#93c5fd" }}>{n.type}</span>{" "}
                <span style={{ color: "#e2e8f0", wordBreak: "break-all" }}>{n.label}</span>
                {typeof n.line === "number" ? <span style={{ color: "#64748b" }}> (line {n.line})</span> : null}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  async function toggleIndividuals(savedGraphId) {
    if (expandedSavedGraphId === savedGraphId) {
      setExpandedSavedGraphId(null);
      setExpandedIndividuals([]);
      setExpandedError("");
      return;
    }
    setExpandedSavedGraphId(savedGraphId);
    setExpandedLoading(true);
    setExpandedError("");
    try {
      const res = await fetch(`${API}/git/ast/${savedGraphId}/`);
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.detail || data.message || "Failed to load individual graphs");
      }
      setExpandedIndividuals(Array.isArray(data.item?.individual_graphs) ? data.item.individual_graphs : []);
    } catch (e) {
      setExpandedIndividuals([]);
      setExpandedError(e.message || "Could not load individual graphs");
    } finally {
      setExpandedLoading(false);
    }
  }

  async function viewIndividualGraph(individualGraphId) {
    setViewGraphOpen(true);
    setViewGraphLoading(true);
    setViewGraphError("");
    setViewGraphData(null);
    try {
      const res = await fetch(`${API}/git/ast/individual/${individualGraphId}/`);
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        throw new Error(data.detail || data.message || "Failed to load individual graph");
      }
      const item = data.item;
      setGraphScale(1);
      setGraphPan({ x: 0, y: 0 });
      setSelectedNodeId(null);
      setViewGraphData({
        repo: item.repo || "unknown/repo",
        ref: item.ref || "unknown",
        node_count: item.node_count,
        edge_count: item.edge_count,
        file_path: item.file_path,
        graph: item.graph || { nodes: [], edges: [] },
        individual_graphs: [],
      });
    } catch (e) {
      setViewGraphError(e.message || "Could not load individual graph");
    } finally {
      setViewGraphLoading(false);
    }
  }

  function downloadAstGraph() {
    if (!astStats?.graph) return;
    const payload = {
      repo: astStats.repo,
      ref: astStats.ref,
      generated_at: astStats.generatedAt,
      ...astStats.graph,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ast_graph.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    loadGitDefaults();
    loadSavedGraphs();
  }, []);

  return (
    <div style={{ fontFamily: "system-ui, Arial, sans-serif", background: "#0f172a", minHeight: "100vh", color: "#e2e8f0" }}>
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "#0f172a",
          borderBottom: "1px solid #1e293b",
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 10, height: 10, borderRadius: 999, background: "#34d399", display: "inline-block" }} />
          <span style={{ fontWeight: 800, color: "#fff" }}>PNOG Demo Service</span>
        </div>
        <Link
          href="/config/git"
          style={{
            background: "#334155",
            border: "1px solid #475569",
            color: "#e2e8f0",
            padding: "8px 12px",
            borderRadius: 10,
            textDecoration: "none",
            fontSize: 13,
            fontWeight: 700,
          }}
        >
          Config
        </Link>
      </header>

      <main style={{ padding: 32, minHeight: "calc(100vh - 56px)" }}>
          <h1 style={{ fontSize: 26, marginBottom: 6, color: "#fff" }}>AST workflow</h1>
          <p style={{ color: "#64748b", marginBottom: 20, fontSize: 14 }}>
            Generate an AST graph from a GitHub repository and branch.
          </p>

      <div style={{ background: "#1e293b", borderRadius: 10, padding: 24, marginBottom: 24, maxWidth: 700 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Generate AST graph from GitHub repo</h2>
        <p style={{ color: "#64748b", marginBottom: 14, fontSize: 13 }}>
          Enter a repo + branch and generate a file/symbol graph (imports, functions, classes).
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: 10, alignItems: "end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700 }}>Repo</label>
            <input
              value={gitRepo}
              onChange={(e) => setGitRepo(e.target.value)}
              placeholder="owner/repo or https://github.com/owner/repo"
              style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 12px", color: "#e2e8f0" }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700 }}>Branch</label>
            <input
              value={gitRef}
              onChange={(e) => setGitRef(e.target.value)}
              placeholder="main"
              style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "10px 12px", color: "#e2e8f0" }}
            />
          </div>
          <button
            onClick={generateAstGraph}
            disabled={astLoading}
            style={{
              height: 40,
              background: astLoading ? "#334155" : "#0f766e",
              border: "1px solid #0d9488",
              color: "#ecfdf5",
              borderRadius: 8,
              padding: "0 14px",
              cursor: astLoading ? "not-allowed" : "pointer",
              fontWeight: 700,
              fontSize: 13,
            }}
          >
            {astLoading ? "Generating..." : "Generate AST"}
          </button>
          <button
            onClick={saveAstGraphToDb}
            disabled={astSaving || !astStats?.graph}
            style={{
              height: 40,
              background: astSaving ? "#334155" : "#2563eb",
              border: "1px solid #1d4ed8",
              color: "#fff",
              borderRadius: 8,
              padding: "0 14px",
              cursor: astSaving || !astStats?.graph ? "not-allowed" : "pointer",
              fontWeight: 700,
              fontSize: 13,
              opacity: !astStats?.graph ? 0.65 : 1,
            }}
          >
            {astSaving ? "Saving..." : "Save to DB"}
          </button>
        </div>
        {astMsg && (
          <p
            style={{
              marginTop: 10,
              fontSize: 13,
              color: astMsg.toLowerCase().includes("failed") || astMsg.toLowerCase().includes("could not")
                ? "#f87171"
                : "#34d399",
            }}
          >
            {astMsg}
          </p>
        )}
        {astStats && (
          <div style={{ marginTop: 12, borderTop: "1px solid #334155", paddingTop: 12 }}>
            <p style={{ margin: "0 0 10px", fontSize: 13, color: "#cbd5e1" }}>
              <strong>{astStats.repo}</strong> @ <strong>{astStats.ref}</strong> | files: {astStats.parsedFiles}/{astStats.scannedFiles} | nodes: {astStats.nodeCount} | edges: {astStats.edgeCount} | function graphs: {astStats.functionGraphCount || 0}
            </p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                onClick={downloadAstGraph}
                style={{ background: "#334155", border: "1px solid #475569", color: "#e2e8f0", padding: "7px 12px", borderRadius: 8, cursor: "pointer", fontSize: 12 }}
              >
                Download graph JSON
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={{ background: "#1e293b", borderRadius: 10, padding: 24, marginBottom: 24, maxWidth: 980 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ fontSize: 16, margin: 0 }}>Saved AST graphs</h2>
          <button
            onClick={loadSavedGraphs}
            disabled={savedLoading}
            style={{
              background: "#334155",
              border: "1px solid #475569",
              color: "#e2e8f0",
              padding: "7px 12px",
              borderRadius: 8,
              cursor: savedLoading ? "not-allowed" : "pointer",
              fontSize: 12,
            }}
          >
            {savedLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {savedGraphs.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>No saved AST graphs yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ color: "#94a3b8", textAlign: "left", borderBottom: "1px solid #334155" }}>
                <th style={{ padding: "8px 6px" }}>Created</th>
                <th style={{ padding: "8px 6px" }}>Repo</th>
                <th style={{ padding: "8px 6px" }}>Ref</th>
                <th style={{ padding: "8px 6px" }}>Nodes</th>
                <th style={{ padding: "8px 6px" }}>Edges</th>
                <th style={{ padding: "8px 6px" }}>Individual</th>
                <th style={{ padding: "8px 6px" }}>Functions</th>
                <th style={{ padding: "8px 6px" }}>ID</th>
                <th style={{ padding: "8px 6px" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {savedGraphs.map((g) => (
                <Fragment key={g.id}>
                  <tr key={g.id} style={{ borderBottom: "1px solid #334155" }}>
                    <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{g.created_at ? new Date(g.created_at).toLocaleString() : "-"}</td>
                    <td style={{ padding: "8px 6px", color: "#e2e8f0" }}>{g.repo}</td>
                    <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{String(g.ref || "").replace("refs/heads/", "")}</td>
                    <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{g.node_count}</td>
                    <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{g.edge_count}</td>
                    <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{g.individual_graphs_count}</td>
                  <td style={{ padding: "8px 6px", color: "#cbd5e1" }}>{g.function_graphs_count || 0}</td>
                    <td style={{ padding: "8px 6px", color: "#94a3b8", fontFamily: "monospace" }}>{g.id.slice(0, 8)}...</td>
                    <td style={{ padding: "8px 6px", display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button
                        onClick={() => viewSavedGraph(g.id)}
                        disabled={viewGraphLoading && viewingGraphId === g.id}
                        style={{
                          background: "#334155",
                          border: "1px solid #475569",
                          color: "#e2e8f0",
                          padding: "5px 9px",
                          borderRadius: 7,
                          cursor: viewGraphLoading && viewingGraphId === g.id ? "not-allowed" : "pointer",
                          fontSize: 12,
                        }}
                      >
                        {viewGraphLoading && viewingGraphId === g.id ? "Loading..." : "View"}
                      </button>
                      <button
                        onClick={() => toggleIndividuals(g.id)}
                        disabled={expandedLoading && expandedSavedGraphId === g.id}
                        style={{
                          background: expandedSavedGraphId === g.id ? "#1d4ed8" : "#334155",
                          border: "1px solid #475569",
                          color: "#e2e8f0",
                          padding: "5px 9px",
                          borderRadius: 7,
                          cursor: expandedLoading && expandedSavedGraphId === g.id ? "not-allowed" : "pointer",
                          fontSize: 12,
                        }}
                      >
                        {expandedLoading && expandedSavedGraphId === g.id ? "Loading..." : expandedSavedGraphId === g.id ? "Hide Individual" : "View Individual"}
                      </button>
                    </td>
                  </tr>
                  {expandedSavedGraphId === g.id && (
                    <tr>
                      <td colSpan={9} style={{ padding: "10px 8px", background: "#0f172a", borderBottom: "1px solid #334155" }}>
                        {expandedError ? (
                          <p style={{ color: "#f87171", margin: 0, fontSize: 12 }}>{expandedError}</p>
                        ) : expandedLoading ? (
                          <p style={{ color: "#94a3b8", margin: 0, fontSize: 12 }}>Loading individual graphs...</p>
                        ) : expandedIndividuals.length === 0 ? (
                          <p style={{ color: "#94a3b8", margin: 0, fontSize: 12 }}>No individual graphs found.</p>
                        ) : (
                          <div style={{ maxHeight: 240, overflow: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
                            {expandedIndividuals.map((f) => (
                              <div key={f.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", border: "1px solid #1e293b", borderRadius: 8, padding: "7px 10px" }}>
                                <div style={{ minWidth: 0 }}>
                                  <p style={{ margin: 0, color: "#e2e8f0", fontSize: 12, wordBreak: "break-all" }}>{f.file_path}</p>
                                  <p style={{ margin: "2px 0 0", color: "#94a3b8", fontSize: 11 }}>
                                    {f.node_count} nodes / {f.edge_count} edges
                                  </p>
                                </div>
                                <button
                                  onClick={() => viewIndividualGraph(f.id)}
                                  style={{
                                    background: "#334155",
                                    border: "1px solid #475569",
                                    color: "#e2e8f0",
                                    padding: "5px 9px",
                                    borderRadius: 7,
                                    cursor: "pointer",
                                    fontSize: 12,
                                    flexShrink: 0,
                                  }}
                                >
                                  View
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {viewGraphOpen && (
        <div
          role="dialog"
          aria-label="Saved AST graph view"
          onClick={closeGraphModal}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            background: "rgba(2, 6, 23, 0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "min(980px, 100%)",
              maxHeight: "85vh",
              overflow: "auto",
              background: "#111827",
              border: "1px solid #334155",
              borderRadius: 12,
              padding: 16,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 16, color: "#fff" }}>Saved Graph Viewer</h3>
              <button onClick={closeGraphModal} style={{ background: "#334155", border: "1px solid #475569", color: "#e2e8f0", padding: "6px 10px", borderRadius: 8, cursor: "pointer", fontSize: 12 }}>
                Close
              </button>
            </div>
            {viewGraphLoading ? (
              <p style={{ color: "#94a3b8", margin: 0 }}>Loading graph...</p>
            ) : viewGraphError ? (
              <p style={{ color: "#f87171", margin: 0 }}>{viewGraphError}</p>
            ) : viewGraphData ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <p style={{ margin: 0, fontSize: 13, color: "#cbd5e1" }}>
                  <strong>{viewGraphData.repo}</strong> @ <strong>{String(viewGraphData.ref || "").replace("refs/heads/", "")}</strong> | nodes: {viewGraphData.node_count} | edges: {viewGraphData.edge_count} | individual: {viewGraphData.individual_graphs?.length || 0}
                </p>
                {viewGraphData.file_path && (
                  <p style={{ margin: 0, fontSize: 12, color: "#93c5fd" }}>
                    File: {viewGraphData.file_path}
                  </p>
                )}
                {renderGraphPreview(viewGraphData.graph)}
                <div style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, padding: 12 }}>
                  <p style={{ margin: "0 0 8px", color: "#94a3b8", fontSize: 12, fontWeight: 700 }}>
                    Individual files ({viewGraphData.individual_graphs?.length || 0})
                  </p>
                  <div style={{ maxHeight: 180, overflow: "auto", fontSize: 12, color: "#cbd5e1" }}>
                    {(viewGraphData.individual_graphs || []).slice(0, 120).map((f) => (
                      <div key={f.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: "4px 0", borderBottom: "1px solid #1e293b" }}>
                        <span style={{ color: "#e2e8f0" }}>{f.file_path}</span>
                        <span style={{ color: "#94a3b8" }}>{f.node_count}n / {f.edge_count}e</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Layer indicator */}
      <div style={{ marginTop: 24, display: "flex", gap: 8, flexWrap: "wrap", maxWidth: 700 }}>
        {[
          ["L0 Network", "#2563eb"], ["L1 App", "#0d9488"], ["L2 Pod", "#7c3aed"],
          ["L3 DB", "#059669"], ["L4 Cache", "#d97706"], ["L5 Git", "#9333ea"],
          ["L6 Frontend", "#dc2626"], ["L7 Metrics", "#ea580c"],
        ].map(([label, color]) => (
          <span key={label} style={{
            background: color + "22", color, border: `1px solid ${color}44`,
            padding: "3px 10px", borderRadius: 10, fontSize: 11, fontWeight: "bold"
          }}>
            {label}
          </span>
        ))}
      </div>
      <p style={{ color: "#334155", fontSize: 11, marginTop: 12 }}>
        Every upload touches all 8 layers. Watch PNOG at localhost:3002
      </p>
      </main>
    </div>
  );
}
