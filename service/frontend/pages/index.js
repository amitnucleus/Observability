import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function Home() {
  const [file, setFile]     = useState(null);
  const [jobs, setJobs]     = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg]       = useState("");

  async function upload() {
    if (!file) return;
    setLoading(true);
    setMsg("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API}/upload/`, { method: "POST", body: form });
      const data = await res.json();
      setMsg(`Job created: ${data.job_id} ${data.cached ? "(cached)" : ""}`);
      loadJobs();
    } catch (e) {
      setMsg(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobs() {
    try {
      const res  = await fetch(`${API}/jobs/`);
      const data = await res.json();
      setJobs(data);
    } catch (e) {
      console.error(e);
    }
  }

  const statusColor = { pending: "#f59e0b", processing: "#3b82f6", done: "#10b981", failed: "#ef4444" };

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
          <h1 style={{ fontSize: 26, marginBottom: 6, color: "#fff" }}>Upload workflow</h1>
          <p style={{ color: "#64748b", marginBottom: 20, fontSize: 14 }}>
            Upload a file, then view jobs and results.
          </p>

      {/* Upload card */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 24, marginBottom: 24, maxWidth: 540 }}>
        <h2 style={{ fontSize: 16, marginBottom: 16 }}>Upload a file</h2>
        <input
          type="file"
          onChange={e => setFile(e.target.files[0])}
          style={{ marginBottom: 12, color: "#94a3b8", display: "block" }}
        />
        <button
          onClick={upload}
          disabled={loading || !file}
          style={{
            background: loading ? "#334155" : "#2563eb",
            color: "#fff", border: "none", borderRadius: 6,
            padding: "10px 24px", cursor: loading ? "not-allowed" : "pointer",
            fontSize: 14,
          }}
        >
          {loading ? "Uploading..." : "Upload & Process"}
        </button>
        {msg && (
          <p style={{ marginTop: 12, fontSize: 13, color: msg.startsWith("Error") ? "#f87171" : "#34d399" }}>
            {msg}
          </p>
        )}
      </div>

      {/* Jobs list */}
      <div style={{ background: "#1e293b", borderRadius: 10, padding: 24, maxWidth: 700 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 16 }}>Recent jobs</h2>
          <button
            onClick={loadJobs}
            style={{ background: "#334155", border: "none", color: "#94a3b8", padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
          >
            ↻ Refresh
          </button>
        </div>

        {jobs.length === 0 ? (
          <p style={{ color: "#475569", fontSize: 13 }}>No jobs yet. Upload a file to start.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", textAlign: "left" }}>
                <th style={{ padding: "6px 8px" }}>File</th>
                <th style={{ padding: "6px 8px" }}>Status</th>
                <th style={{ padding: "6px 8px" }}>Job ID</th>
                <th style={{ padding: "6px 8px" }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.job_id} style={{ borderTop: "1px solid #334155" }}>
                  <td style={{ padding: "8px" }}>{j.filename}</td>
                  <td style={{ padding: "8px" }}>
                    <span style={{
                      background: statusColor[j.status] + "22",
                      color: statusColor[j.status] || "#94a3b8",
                      padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: "bold"
                    }}>
                      {j.status}
                    </span>
                  </td>
                  <td style={{ padding: "8px", fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>
                    {j.job_id.slice(0, 8)}...
                  </td>
                  <td style={{ padding: "8px", color: "#64748b" }}>
                    {new Date(j.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

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
