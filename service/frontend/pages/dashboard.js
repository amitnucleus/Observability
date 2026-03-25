import { useState } from "react";
import Link from "next/link";
import {
  systemSummary,
  blastRadius,
  applicationsSummary,
  infrastructureMock,
  networkMock,
} from "../data/dashboardMock";

/** Stable across SSR and browser (avoids hydration mismatch from locale / timezone defaults). */
function formatUtc(isoString) {
  return new Date(isoString).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function formatInt(n) {
  return n.toLocaleString("en-US");
}

const tabs = [
  { id: "summary", label: "Summary" },
  { id: "application", label: "Application" },
  { id: "infrastructure", label: "Infrastructure" },
  { id: "network", label: "Network" },
];

const statusStyles = {
  healthy: { bg: "#10b98122", color: "#34d399", border: "#10b98144" },
  degraded: { bg: "#f59e0b22", color: "#fbbf24", border: "#f59e0b44" },
  critical: { bg: "#ef444422", color: "#f87171", border: "#ef444444" },
  pressure: { bg: "#f59e0b22", color: "#fbbf24", border: "#f59e0b44" },
  root: "#dc2626",
  direct: "#ea580c",
  transitive: "#d97706",
  edge: "#64748b",
  "user-visible": "#a855f7",
};

function Badge({ children, variant = "healthy" }) {
  const s = statusStyles[variant] || statusStyles.healthy;
  return (
    <span
      style={{
        display: "inline-block",
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        textTransform: "capitalize",
      }}
    >
      {children}
    </span>
  );
}

function Card({ title, children, style = {} }) {
  return (
    <div
      style={{
        background: "#1e293b",
        borderRadius: 10,
        padding: 20,
        border: "1px solid #334155",
        ...style,
      }}
    >
      {title && (
        <h2 style={{ fontSize: 14, color: "#94a3b8", marginBottom: 14, fontWeight: 600 }}>{title}</h2>
      )}
      {children}
    </div>
  );
}

function SummaryTab() {
  const sys = systemSummary;
  const br = blastRadius;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <Card title="Overall system">
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <Badge variant={sys.overallStatus === "healthy" ? "healthy" : "degraded"}>{sys.overallStatus}</Badge>
            <span style={{ color: "#cbd5e1", fontSize: 13 }}>{sys.statusMessage}</span>
          </div>
          <p style={{ color: "#64748b", fontSize: 12, marginTop: 12 }}>
            Last notable event: {formatUtc(sys.lastIncidentAt)}
          </p>
        </Card>
        <Card title="SLO & alerts">
          <p style={{ fontSize: 28, fontWeight: 700, color: "#fff", margin: 0 }}>
            {sys.sloBudgetRemaining.month}
            <span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 400 }}>{sys.sloBudgetRemaining.unit} budget</span>
          </p>
          <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 8 }}>
            {sys.activeAlerts} active alerts · {sys.healthyApps}/{sys.totalApps} apps healthy
          </p>
        </Card>
      </div>

      <Card title="Blast radius (mock RCA)">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 24, alignItems: "start" }}>
          <div>
            <p style={{ color: "#64748b", fontSize: 12, marginBottom: 8 }}>Fault origin</p>
            <p style={{ fontSize: 18, fontWeight: 600, color: "#fff", margin: 0 }}>{br.faultOrigin.name}</p>
            <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 4 }}>
              {br.faultOrigin.layer} · <Badge variant="degraded">{br.faultOrigin.severity}</Badge>
            </p>
            <p style={{ color: "#64748b", fontSize: 12, marginTop: 16 }}>
              {br.hopCount} dependency hops · {br.affectedCount} components in radius
            </p>
          </div>
          <div>
            <p style={{ color: "#64748b", fontSize: 12, marginBottom: 10 }}>Affected components</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {br.affected.map((a) => (
                <div
                  key={a.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    background: "#0f172a",
                    borderRadius: 8,
                    borderLeft: `3px solid ${statusStyles[a.impact] || "#64748b"}`,
                  }}
                >
                  <div>
                    <span style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 500 }}>{a.name}</span>
                    <span style={{ color: "#475569", fontSize: 11, marginLeft: 8 }}>{a.type}</span>
                  </div>
                  <span style={{ color: "#94a3b8", fontSize: 11, textTransform: "capitalize" }}>{a.impact}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <Card title="All applications (summary)">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "#64748b", textAlign: "left" }}>
                <th style={{ padding: "8px 10px" }}>Application</th>
                <th style={{ padding: "8px 10px" }}>Env</th>
                <th style={{ padding: "8px 10px" }}>Status</th>
                <th style={{ padding: "8px 10px" }}>RPS</th>
                <th style={{ padding: "8px 10px" }}>p99 (ms)</th>
                <th style={{ padding: "8px 10px" }}>Errors %</th>
              </tr>
            </thead>
            <tbody>
              {applicationsSummary.map((app) => (
                <tr key={app.name} style={{ borderTop: "1px solid #334155" }}>
                  <td style={{ padding: "10px", color: "#e2e8f0", fontWeight: 500 }}>{app.name}</td>
                  <td style={{ padding: "10px", color: "#64748b" }}>{app.env}</td>
                  <td style={{ padding: "10px" }}>
                    <Badge variant={app.status === "healthy" ? "healthy" : "degraded"}>{app.status}</Badge>
                  </td>
                  <td style={{ padding: "10px", color: "#cbd5e1" }}>{formatInt(app.rps)}</td>
                  <td style={{ padding: "10px", color: "#cbd5e1" }}>{app.p99Ms}</td>
                  <td style={{ padding: "10px", color: app.errorRate > 0.5 ? "#f87171" : "#94a3b8" }}>{app.errorRate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function ApplicationTab() {
  return (
    <Card>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>
        Per-service runtime view (mock). Wire to traces, logs, and golden signals.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748b", textAlign: "left" }}>
              <th style={{ padding: "8px 10px" }}>Service</th>
              <th style={{ padding: "8px 10px" }}>Version</th>
              <th style={{ padding: "8px 10px" }}>Status</th>
              <th style={{ padding: "8px 10px" }}>RPS</th>
              <th style={{ padding: "8px 10px" }}>p99 latency</th>
              <th style={{ padding: "8px 10px" }}>Error rate</th>
            </tr>
          </thead>
          <tbody>
            {applicationsSummary.map((app) => (
              <tr key={app.name} style={{ borderTop: "1px solid #334155" }}>
                <td style={{ padding: "10px", color: "#e2e8f0" }}>{app.name}</td>
                <td style={{ padding: "10px", fontFamily: "monospace", fontSize: 12, color: "#94a3b8" }}>{app.version}</td>
                <td style={{ padding: "10px" }}>
                  <Badge variant={app.status === "healthy" ? "healthy" : "degraded"}>{app.status}</Badge>
                </td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{formatInt(app.rps)}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{app.p99Ms} ms</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{app.errorRate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function InfrastructureTab() {
  const { clusters, nodes, storage } = infrastructureMock;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card title="Kubernetes clusters">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
          {clusters.map((c) => (
            <div key={c.name} style={{ background: "#0f172a", padding: 16, borderRadius: 8 }}>
              <p style={{ margin: 0, fontWeight: 600, color: "#fff" }}>{c.name}</p>
              <p style={{ margin: "6px 0 0", fontSize: 12, color: "#64748b" }}>{c.provider}</p>
              <p style={{ margin: "12px 0 0", fontSize: 13, color: "#94a3b8" }}>
                Nodes: {c.nodes} · Pods ready: {c.podsReady}
              </p>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#94a3b8" }}>
                CPU {c.cpuUtil}% · Memory {c.memUtil}%
              </p>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Nodes (sample)">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748b", textAlign: "left" }}>
              <th style={{ padding: "8px 10px" }}>Node</th>
              <th style={{ padding: "8px 10px" }}>Role</th>
              <th style={{ padding: "8px 10px" }}>CPU %</th>
              <th style={{ padding: "8px 10px" }}>Mem %</th>
              <th style={{ padding: "8px 10px" }}>Disk %</th>
              <th style={{ padding: "8px 10px" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.name} style={{ borderTop: "1px solid #334155" }}>
                <td style={{ padding: "10px", fontFamily: "monospace", fontSize: 11, color: "#94a3b8" }}>{n.name}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{n.role}</td>
                <td style={{ padding: "10px", color: n.cpu > 85 ? "#f87171" : "#cbd5e1" }}>{n.cpu}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{n.mem}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{n.disk}</td>
                <td style={{ padding: "10px" }}>
                  <Badge variant={n.status === "ready" ? "healthy" : "degraded"}>{n.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card title="Storage">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748b", textAlign: "left" }}>
              <th style={{ padding: "8px 10px" }}>Volume</th>
              <th style={{ padding: "8px 10px" }}>Type</th>
              <th style={{ padding: "8px 10px" }}>Used</th>
              <th style={{ padding: "8px 10px" }}>Capacity</th>
              <th style={{ padding: "8px 10px" }}>IOPS</th>
            </tr>
          </thead>
          <tbody>
            {storage.map((s) => (
              <tr key={s.name} style={{ borderTop: "1px solid #334155" }}>
                <td style={{ padding: "10px", color: "#e2e8f0" }}>{s.name}</td>
                <td style={{ padding: "10px", color: "#94a3b8" }}>{s.type}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{s.usedTiB} TiB</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{s.capacityTiB}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{s.iops}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function NetworkTab() {
  const { regions, ingress, egress, dns } = networkMock;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <Card title="Ingress (edge → origin)">
          <p style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#fff" }}>{formatInt(ingress.rps)} rps</p>
          <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 8 }}>{ingress.bandwidthGbps} Gbps · TLS p99 {ingress.tlsHandshakeP99Ms} ms</p>
        </Card>
        <Card title="Egress">
          <p style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#fff" }}>{formatInt(egress.rps)} rps</p>
          <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 8 }}>
            {egress.bandwidthGbps} Gbps · top: {egress.topDestination}
          </p>
        </Card>
        <Card title="DNS">
          <p style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#fff" }}>{formatInt(dns.queriesPerSec)} qps</p>
          <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 8 }}>
            NXDOMAIN {dns.nxdomainRate}% · p99 {dns.p99ResolutionMs} ms
          </p>
        </Card>
      </div>
      <Card title="Region / path latency (mock)">
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ color: "#64748b", textAlign: "left" }}>
              <th style={{ padding: "8px 10px" }}>From</th>
              <th style={{ padding: "8px 10px" }}>To</th>
              <th style={{ padding: "8px 10px" }}>RTT (ms)</th>
              <th style={{ padding: "8px 10px" }}>Jitter (ms)</th>
              <th style={{ padding: "8px 10px" }}>Loss %</th>
              <th style={{ padding: "8px 10px" }}>Throughput</th>
            </tr>
          </thead>
          <tbody>
            {regions.map((r, i) => (
              <tr key={i} style={{ borderTop: "1px solid #334155" }}>
                <td style={{ padding: "10px", color: "#e2e8f0" }}>{r.from}</td>
                <td style={{ padding: "10px", color: "#e2e8f0" }}>{r.to}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{r.latencyMs}</td>
                <td style={{ padding: "10px", color: "#cbd5e1" }}>{r.jitterMs}</td>
                <td style={{ padding: "10px", color: r.lossPct > 0 ? "#fbbf24" : "#94a3b8" }}>{r.lossPct}</td>
                <td style={{ padding: "10px", color: "#94a3b8" }}>{r.throughputGbps} Gbps</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export default function DashboardPage() {
  const [tab, setTab] = useState("summary");

  return (
    <div style={{ fontFamily: "system-ui, Arial, sans-serif", background: "#0f172a", minHeight: "100vh", color: "#e2e8f0" }}>
      <header
        style={{
          borderBottom: "1px solid #334155",
          padding: "16px 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1 style={{ fontSize: 20, margin: 0, color: "#fff" }}>Observability dashboard</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>Unified view · mock data</p>
        </div>
        <Link
          href="/"
          style={{ fontSize: 13, color: "#60a5fa", textDecoration: "none" }}
        >
          ← Demo service
        </Link>
      </header>

      <nav
        style={{
          display: "flex",
          gap: 4,
          padding: "12px 28px 0",
          borderBottom: "1px solid #1e293b",
          flexWrap: "wrap",
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            style={{
              background: tab === t.id ? "#1e293b" : "transparent",
              color: tab === t.id ? "#fff" : "#94a3b8",
              border: "1px solid",
              borderColor: tab === t.id ? "#475569" : "transparent",
              borderBottom: tab === t.id ? "1px solid #0f172a" : undefined,
              marginBottom: -1,
              padding: "10px 18px",
              borderRadius: "8px 8px 0 0",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: tab === t.id ? 600 : 500,
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main style={{ padding: 28, maxWidth: 1200, margin: "0 auto" }}>
        {tab === "summary" && <SummaryTab />}
        {tab === "application" && <ApplicationTab />}
        {tab === "infrastructure" && <InfrastructureTab />}
        {tab === "network" && <NetworkTab />}
      </main>
    </div>
  );
}
