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

export default function ConfigGitPage() {
  const [repo, setRepo] = useState("pnog/demo-service");
  const [ref, setRef] = useState("refs/heads/main");
  const [githubToken, setGithubToken] = useState("");
  const [githubTokenPresent, setGithubTokenPresent] = useState(false);
  const [status, setStatus] = useState("");
  const [checking, setChecking] = useState(false);

  async function parseJsonOrText(res) {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      return res.json();
    }
    const text = await res.text();
    throw new Error(`Expected JSON (${res.status}): ${text.slice(0, 200)}`);
  }

  async function load() {
    setStatus("");
    try {
      const res = await fetch(`${API}/git/config/`);
      if (!res.ok) throw new Error(await res.text());
      const cfg = await parseJsonOrText(res);
      setRepo(cfg.repo || "pnog/demo-service");
      setRef(cfg.ref || "refs/heads/main");
      setGithubTokenPresent(Boolean(cfg.github_token_present));
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
        body: JSON.stringify({ repo, ref, github_token: githubToken || null }),
      });
      if (!res.ok) throw new Error(await res.text());
      await parseJsonOrText(res);
      setStatus("Saved.");
      setGithubToken("");
      await load();
    } catch (e) {
      setStatus(`Save failed: ${String(e?.message || e)}`);
    }
  }

  async function checkConnectivity() {
    setChecking(true);
    setStatus("");
    try {
      const res = await fetch(`${API}/git/connectivity/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo, ref, github_token: githubToken || null }),
      });
      const data = await parseJsonOrText(res);
      if (data.ok) {
        setStatus(
          `Git OK: ${data.message} — ${data.repo} @ ${data.ref} (commit ${data.commit_sha?.slice(0, 7) || "?"})`
        );
      } else {
        setStatus(`Git check failed: ${data.message || "unknown"}`);
      }
    } catch (e) {
      setStatus(`Could not reach backend: ${String(e?.message || e)}`);
    } finally {
      setChecking(false);
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
          <Link
            href="/config/git"
            style={{
              display: "block",
              background: "#111827",
              border: "1px solid #334155",
              color: "#e2e8f0",
              padding: "10px 12px",
              borderRadius: 10,
              textDecoration: "none",
              fontSize: 13,
              fontWeight: 800,
            }}
          >
            Git
          </Link>
        </aside>

        <main style={{ padding: 32, maxWidth: 860 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 22, color: "#fff" }}>Git settings</h1>
              <p style={{ margin: "8px 0 0", color: "#64748b", fontSize: 13 }}>
                Configure repo + branch so the app can fetch the latest commit from GitHub (AST and other flows use this).
                Use <strong style={{ color: "#94a3b8" }}>Check connectivity</strong> to verify before saving.
              </p>
            </div>

            <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: 18 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Field label="Repo" value={repo} onChange={setRepo} placeholder="owner/repo or https://github.com/owner/repo" />
                <Field label="Ref / branch" value={ref} onChange={setRef} placeholder="refs/heads/main or main" />
              </div>

              <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700 }}>
                    GitHub token{" "}
                    <span style={{ color: githubTokenPresent ? "#34d399" : "#64748b", fontWeight: 800 }}>
                      {githubTokenPresent ? "(stored)" : "(not set)"}
                    </span>
                  </label>
                  <input
                    type="password"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder={githubTokenPresent ? "enter new token to replace" : "enter token"}
                    style={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 10,
                      padding: "10px 12px",
                      color: "#e2e8f0",
                    }}
                  />
                  <p style={{ margin: 0, fontSize: 12, color: "#64748b" }}>
                    Needed for private repos or to avoid GitHub rate limits. Stored in-memory only (current process).
                  </p>
                </div>
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
                  onClick={checkConnectivity}
                  disabled={checking}
                  style={{
                    background: checking ? "#1e293b" : "#0f766e",
                    border: "1px solid #0d9488",
                    color: "#ecfdf5",
                    padding: "10px 14px",
                    borderRadius: 10,
                    cursor: checking ? "not-allowed" : "pointer",
                    fontWeight: 800,
                    fontSize: 13,
                  }}
                >
                  {checking ? "Checking…" : "Check connectivity"}
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
                <p
                  style={{
                    margin: "12px 0 0",
                    color:
                      status.startsWith("Saved") || status.startsWith("Git OK")
                        ? "#34d399"
                        : status.startsWith("Git check failed")
                          ? "#f87171"
                          : "#fbbf24",
                    fontSize: 13,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {status}
                </p>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
