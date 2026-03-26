import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function Field({ label, value, onChange, placeholder }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700 }}>{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          background: "#0f172a",
          border: "1px solid #334155",
          borderRadius: 10,
          padding: "10px 12px",
          color: "#e2e8f0",
        }}
      />
    </div>
  );
}

export default function ConfigPage() {
  const [active, setActive] = useState("git");
  const [repo, setRepo] = useState("pnog/demo-service");
  const [ref, setRef] = useState("refs/heads/main");
  const [commit, setCommit] = useState("");
  const [compare, setCompare] = useState("");
  const [status, setStatus] = useState("");

  async function load() {
    setStatus("");
    try {
      const res = await fetch(`${API}/git/config/`);
      if (!res.ok) throw new Error(await res.text());
      const cfg = await res.json();
      setRepo(cfg.repo || "pnog/demo-service");
      setRef(cfg.ref || "refs/heads/main");
      setCommit(cfg.commit || "");
      setCompare(cfg.compare || "");
    } catch (e) {
      setStatus(`Could not load backend config: ${String(e?.message || e)}`);
    }
  }

  async function save() {
    setStatus("");
    try {
      const res = await fetch(`${API}/git/config/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo, ref, commit: commit || null, compare }),
      });
      if (!res.ok) throw new Error(await res.text());
      setStatus("Saved.");
    } catch (e) {
      setStatus(`Save failed: ${String(e?.message || e)}`);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          <span style={{ width: 10, height: 10, borderRadius: 999, background: "#60a5fa", display: "inline-block" }} />
          <span style={{ fontWeight: 800, color: "#fff" }}>Config</span>
        </div>
        <Link href="/" style={{ color: "#94a3b8", textDecoration: "none", fontSize: 13, fontWeight: 700 }}>
          ← Home
        </Link>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", minHeight: "calc(100vh - 56px)" }}>
        <aside style={{ borderRight: "1px solid #1e293b", padding: 16 }}>
          <button
            type="button"
            onClick={() => setActive("git")}
            style={{
              width: "100%",
              textAlign: "left",
              background: active === "git" ? "#111827" : "transparent",
              border: "1px solid",
              borderColor: active === "git" ? "#334155" : "transparent",
              color: active === "git" ? "#e2e8f0" : "#94a3b8",
              padding: "10px 12px",
              borderRadius: 10,
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            Git
          </button>
        </aside>

        <main style={{ padding: 32, maxWidth: 860 }}>
          {active === "git" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <h1 style={{ margin: 0, fontSize: 22, color: "#fff" }}>Git settings</h1>
                <p style={{ margin: "8px 0 0", color: "#64748b", fontSize: 13 }}>
                  Configure repo + branch so the app can fetch the latest commit snapshot from GitHub.
                </p>
              </div>

              <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: 18 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <Field label="Repo" value={repo} onChange={setRepo} placeholder="owner/repo" />
                  <Field label="Ref / branch" value={ref} onChange={setRef} placeholder="refs/heads/main or main" />
                  <Field label="Commit (optional)" value={commit} onChange={setCommit} placeholder="leave blank" />
                  <Field label="Compare (optional)" value={compare} onChange={setCompare} placeholder="leave blank" />
                </div>

                <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 16, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={load}
                    style={{
                      background: "transparent",
                      border: "1px solid #475569",
                      color: "#e2e8f0",
                      padding: "10px 14px",
                      borderRadius: 10,
                      cursor: "pointer",
                      fontWeight: 800,
                      fontSize: 13,
                    }}
                  >
                    Reload
                  </button>
                  <button
                    type="button"
                    onClick={save}
                    style={{
                      background: "#2563eb",
                      border: "none",
                      color: "#fff",
                      padding: "10px 14px",
                      borderRadius: 10,
                      cursor: "pointer",
                      fontWeight: 900,
                      fontSize: 13,
                    }}
                  >
                    Save
                  </button>
                </div>

                {status && (
                  <p style={{ margin: "12px 0 0", color: status.startsWith("Saved") ? "#34d399" : "#fbbf24", fontSize: 13 }}>
                    {status}
                  </p>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

