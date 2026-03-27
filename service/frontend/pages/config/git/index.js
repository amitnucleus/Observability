import { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

function InfoIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" />
      <path
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        d="M12 16v-4M12 8h.01"
      />
    </svg>
  );
}

const inputStyle = {
  background: "#0f172a",
  border: "1px solid #334155",
  borderRadius: 10,
  padding: "10px 12px",
  color: "#e2e8f0",
};

const popoverStyle = {
  position: "absolute",
  left: 0,
  top: "100%",
  marginTop: 6,
  zIndex: 20,
  maxWidth: 440,
  padding: "14px 16px",
  borderRadius: 10,
  border: "1px solid #475569",
  background: "#0f172a",
  boxShadow: "0 12px 40px rgba(0,0,0,0.45)",
  fontSize: 13,
  lineHeight: 1.55,
  color: "#cbd5e1",
};

function InfoButton({ active, ariaLabel, onToggle }) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      aria-expanded={active}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 26,
        height: 26,
        padding: 0,
        borderRadius: 999,
        border: "1px solid #475569",
        background: active ? "#334155" : "#1e293b",
        color: "#94a3b8",
        cursor: "pointer",
        flexShrink: 0,
      }}
    >
      <InfoIcon />
    </button>
  );
}

function FieldWithInfo({
  label,
  value,
  onChange,
  placeholder,
  helpKey,
  helpOpen,
  setHelpOpen,
  helpTitle,
  children,
  hintBelow,
}) {
  const open = helpOpen === helpKey;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700, margin: 0 }}>{label}</label>
        <InfoButton
          active={open}
          ariaLabel={helpTitle}
          onToggle={() => setHelpOpen((k) => (k === helpKey ? null : helpKey))}
        />
      </div>
      {open && (
        <div role="dialog" aria-label={helpTitle} onClick={(e) => e.stopPropagation()} style={popoverStyle}>
          <p style={{ margin: "0 0 10px", fontWeight: 800, color: "#f1f5f9" }}>{helpTitle}</p>
          {children}
        </div>
      )}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={inputStyle}
      />
      {hintBelow ? (
        <p style={{ margin: 0, fontSize: 11, lineHeight: 1.45, color: "#94a3b8" }}>{hintBelow}</p>
      ) : null}
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
  const HELP = { repo: "repo", ref: "ref", token: "token" };
  const [helpOpen, setHelpOpen] = useState(null);

  useEffect(() => {
    if (!helpOpen) return;
    const close = () => setHelpOpen(null);
    const id = setTimeout(() => document.addEventListener("click", close), 0);
    return () => {
      clearTimeout(id);
      document.removeEventListener("click", close);
    };
  }, [helpOpen]);

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
                <FieldWithInfo
                  label="Repo"
                  value={repo}
                  onChange={setRepo}
                  placeholder="owner/repo or https://github.com/owner/repo"
                  helpKey={HELP.repo}
                  helpOpen={helpOpen}
                  setHelpOpen={setHelpOpen}
                  helpTitle="Repository — accepted formats"
                >
                  <p style={{ margin: "0 0 10px" }}>
                    The app resolves the GitHub repository from a short name or a GitHub URL. Use the same values you see on the
                    repo home page.
                  </p>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>Short form:</strong> <code style={{ color: "#93c5fd" }}>owner/repo</code>{" "}
                      — e.g. <code style={{ color: "#93c5fd" }}>pnog/demo-service</code>,{" "}
                      <code style={{ color: "#93c5fd" }}>microsoft/vscode</code>
                    </li>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>HTTPS URL:</strong>{" "}
                      <code style={{ color: "#93c5fd" }}>https://github.com/owner/repo</code>
                    </li>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>HTTP URL:</strong>{" "}
                      <code style={{ color: "#93c5fd" }}>http://github.com/owner/repo</code>
                    </li>
                    <li style={{ marginBottom: 6 }}>
                      Only the <strong style={{ color: "#e2e8f0" }}>owner</strong> and <strong style={{ color: "#e2e8f0" }}>repository name</strong>{" "}
                      are used. Do not put branches, <code style={{ color: "#93c5fd" }}>/tree/…</code>, issues, or{" "}
                      <code style={{ color: "#93c5fd" }}>.git</code> here — put the branch in <strong style={{ color: "#e2e8f0" }}>Ref / branch</strong>.
                    </li>
                  </ul>
                </FieldWithInfo>
                <FieldWithInfo
                  label="Ref / branch"
                  value={ref}
                  onChange={setRef}
                  placeholder="main"
                  hintBelow={
                    <>
                      Use the <strong style={{ color: "#cbd5e1" }}>Git branch</strong> from GitHub’s branch menu (usually{" "}
                      <strong style={{ color: "#cbd5e1" }}>main</strong> or <strong style={{ color: "#cbd5e1" }}>master</strong>
                      ). Not a folder name like <code style={{ color: "#fbbf24" }}>app</code>, <code style={{ color: "#fbbf24" }}>pnog</code>
                      , or <code style={{ color: "#fbbf24" }}>service</code>.
                    </>
                  }
                  helpKey={HELP.ref}
                  helpOpen={helpOpen}
                  setHelpOpen={setHelpOpen}
                  helpTitle="Branch / ref — accepted formats"
                >
                  <p
                    style={{
                      margin: "0 0 10px",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #854d0e",
                      background: "#422006",
                      color: "#fde68a",
                      fontSize: 12,
                    }}
                  >
                    <strong style={{ color: "#fef08a" }}>Common mistake:</strong> do not put a <strong>folder inside the repo</strong>{" "}
                    here (e.g. <code style={{ color: "#fde68a" }}>app</code>, <code style={{ color: "#fde68a" }}>pnog</code>,{" "}
                    <code style={{ color: "#fde68a" }}>src</code>) — those are directories, not branches. This field must be the{" "}
                    <strong>branch name</strong> exactly as in GitHub’s branch dropdown — almost always{" "}
                    <code style={{ color: "#fde68a" }}>main</code> or <code style={{ color: "#fde68a" }}>master</code>.
                  </p>
                  <p style={{ margin: "0 0 10px" }}>
                    Connectivity checks the <strong style={{ color: "#e2e8f0" }}>latest commit on a branch</strong> (GitHub{" "}
                    <code style={{ color: "#93c5fd" }}>commits/&lt;branch&gt;</code>). The backend normalizes values to{" "}
                    <code style={{ color: "#93c5fd" }}>refs/heads/&lt;branch&gt;</code> when you omit the prefix.
                  </p>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>Branch name only:</strong>{" "}
                      <code style={{ color: "#93c5fd" }}>main</code>, <code style={{ color: "#93c5fd" }}>master</code>,{" "}
                      <code style={{ color: "#93c5fd" }}>develop</code>
                    </li>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>Branch with slashes:</strong>{" "}
                      <code style={{ color: "#93c5fd" }}>feature/auth</code>, <code style={{ color: "#93c5fd" }}>release/v2</code>
                    </li>
                    <li style={{ marginBottom: 6 }}>
                      <strong style={{ color: "#e2e8f0" }}>Full ref (heads):</strong>{" "}
                      <code style={{ color: "#93c5fd" }}>refs/heads/main</code>,{" "}
                      <code style={{ color: "#93c5fd" }}>refs/heads/feature/auth</code>
                    </li>
                    <li style={{ marginBottom: 0 }}>
                      <strong style={{ color: "#e2e8f0" }}>Already normalized:</strong> if you enter{" "}
                      <code style={{ color: "#93c5fd" }}>refs/heads/…</code>, it is kept as-is. Tag-only refs like{" "}
                      <code style={{ color: "#93c5fd" }}>refs/tags/v1.0.0</code> are not used by the current branch commit check.
                    </li>
                  </ul>
                </FieldWithInfo>
              </div>

              <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, position: "relative" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <label style={{ fontSize: 12, color: "#94a3b8", fontWeight: 700, margin: 0 }}>
                      GitHub token{" "}
                      <span style={{ color: githubTokenPresent ? "#34d399" : "#64748b", fontWeight: 800 }}>
                        {githubTokenPresent ? "(stored)" : "(not set)"}
                      </span>
                    </label>
                    <InfoButton
                      active={helpOpen === HELP.token}
                      ariaLabel="How to set up a GitHub token"
                      onToggle={() => setHelpOpen((k) => (k === HELP.token ? null : HELP.token))}
                    />
                  </div>
                  {helpOpen === HELP.token && (
                    <div role="dialog" aria-label="GitHub token setup" onClick={(e) => e.stopPropagation()} style={popoverStyle}>
                      <p style={{ margin: "0 0 10px", fontWeight: 800, color: "#f1f5f9" }}>Setting up a GitHub token</p>
                      <p style={{ margin: "0 0 12px", padding: "10px 12px", borderRadius: 8, background: "#1e3a5f", color: "#bfdbfe", fontSize: 12, lineHeight: 1.5 }}>
                        <strong style={{ color: "#dbeafe" }}>Private repos:</strong> connectivity uses the GitHub REST API with{" "}
                        <code style={{ color: "#93c5fd" }}>Authorization: Bearer &lt;token&gt;</code>. Without a token, private repos
                        return 404. Paste a token with access to this repository, then <strong style={{ color: "#dbeafe" }}>Save</strong>
                        , then <strong style={{ color: "#dbeafe" }}>Check connectivity</strong>.
                      </p>
                      <ol style={{ margin: 0, paddingLeft: 18 }}>
                        <li style={{ marginBottom: 8 }}>
                          Open{" "}
                          <a
                            href="https://github.com/settings/tokens"
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "#60a5fa" }}
                          >
                            GitHub → Settings → Developer settings → Personal access tokens
                          </a>
                          .
                        </li>
                        <li style={{ marginBottom: 8 }}>
                          <strong style={{ color: "#e2e8f0" }}>Fine-grained token:</strong> choose the owner/org, select only the
                          target repository, and grant <strong style={{ color: "#e2e8f0" }}>Contents: Read</strong> (read commit
                          metadata). <strong style={{ color: "#e2e8f0" }}>Classic token:</strong> enable the{" "}
                          <strong style={{ color: "#e2e8f0" }}>repo</strong> scope (full control of private repositories) — or a
                          narrower classic scope your org allows.
                        </li>
                        <li style={{ marginBottom: 8 }}>
                          The GitHub account that owns the token must have access to the repo (same org membership, or collaborator
                          on a private fork).
                        </li>
                        <li style={{ marginBottom: 8 }}>
                          Copy the token once GitHub shows it (you will not see it again). Paste it here and click{" "}
                          <strong style={{ color: "#e2e8f0" }}>Save</strong> so it is stored server-side.
                        </li>
                        <li>
                          Authenticated requests have higher rate limits than anonymous calls. Treat the token like a password and
                          rotate it if it may have leaked.
                        </li>
                      </ol>
                    </div>
                  )}
                  <input
                    type="password"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder={githubTokenPresent ? "enter new token to replace" : "enter token"}
                    style={inputStyle}
                  />
                  <p style={{ margin: 0, fontSize: 12, color: "#64748b" }}>
                    <strong style={{ color: "#94a3b8" }}>Private repo:</strong> create a PAT with access to this repo (fine-grained:
                    Contents read; classic: <code style={{ color: "#93c5fd" }}>repo</code>), paste above, <strong style={{ color: "#94a3b8" }}>Save</strong>
                    , then <strong style={{ color: "#94a3b8" }}>Check connectivity</strong>. Also helps with public-repo rate limits.
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
