import Link from "next/link";

export default function ConfigIndexPage() {
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

        <main style={{ padding: 32, maxWidth: 720 }}>
          <h1 style={{ margin: "0 0 8px", fontSize: 22, color: "#fff" }}>Configuration</h1>
          <p style={{ margin: 0, color: "#64748b", fontSize: 14 }}>
            Choose a section from the left, or open{" "}
            <Link href="/config/git" style={{ color: "#60a5fa" }}>
              Git settings
            </Link>
            .
          </p>
        </main>
      </div>
    </div>
  );
}
