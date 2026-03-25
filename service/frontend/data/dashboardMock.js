/** Mock data for the observability dashboard — replace with API calls later */

export const systemSummary = {
  overallStatus: "degraded",
  statusMessage: "2 services elevated error rate; no customer-facing outage",
  lastIncidentAt: "2026-03-23T14:22:00Z",
  sloBudgetRemaining: { month: 98.4, unit: "%" },
  activeAlerts: 3,
  healthyApps: 6,
  totalApps: 8,
};

export const blastRadius = {
  faultOrigin: {
    id: "svc-payment",
    name: "payment-api",
    layer: "Application",
    severity: "high",
  },
  hopCount: 3,
  affectedCount: 7,
  affected: [
    { id: "svc-payment", name: "payment-api", type: "service", impact: "root" },
    { id: "svc-orders", name: "order-service", type: "service", impact: "direct" },
    { id: "svc-inventory", name: "inventory-api", type: "service", impact: "transitive" },
    { id: "db-orders-primary", name: "orders-pg-primary", type: "database", impact: "transitive" },
    { id: "cache-session", name: "redis-session", type: "cache", impact: "transitive" },
    { id: "queue-async", name: "kafka-async-workers", type: "messaging", impact: "edge" },
    { id: "fe-checkout", name: "checkout-web", type: "frontend", impact: "user-visible" },
  ],
};

export const applicationsSummary = [
  { name: "api-gateway", env: "prod", status: "healthy", rps: 4200, p99Ms: 45, errorRate: 0.02, version: "2.14.1" },
  { name: "auth-service", env: "prod", status: "healthy", rps: 890, p99Ms: 120, errorRate: 0.01, version: "1.8.0" },
  { name: "payment-api", env: "prod", status: "degraded", rps: 2100, p99Ms: 890, errorRate: 2.1, version: "3.2.0" },
  { name: "order-service", env: "prod", status: "degraded", rps: 1800, p99Ms: 520, errorRate: 0.8, version: "4.1.2" },
  { name: "notification-worker", env: "prod", status: "healthy", rps: 340, p99Ms: 210, errorRate: 0.0, version: "0.9.4" },
  { name: "search-indexer", env: "prod", status: "healthy", rps: 120, p99Ms: 1800, errorRate: 0.05, version: "1.0.11" },
  { name: "checkout-web", env: "prod", status: "healthy", rps: 950, p99Ms: 95, errorRate: 0.03, version: "2026.03.1" },
  { name: "admin-console", env: "staging", status: "healthy", rps: 12, p99Ms: 200, errorRate: 0.0, version: "0.4.0" },
];

export const infrastructureMock = {
  clusters: [
    { name: "prod-use1", provider: "AWS", nodes: 24, cpuUtil: 61, memUtil: 72, podsReady: "118/120" },
    { name: "prod-euw1", provider: "AWS", nodes: 12, cpuUtil: 48, memUtil: 55, podsReady: "56/56" },
  ],
  nodes: [
    { name: "ip-10-0-12-44.ec2.internal", role: "worker", cpu: 78, mem: 64, disk: 42, status: "ready" },
    { name: "ip-10-0-13-02.ec2.internal", role: "worker", cpu: 52, mem: 71, disk: 38, status: "ready" },
    { name: "ip-10-0-11-88.ec2.internal", role: "worker", cpu: 91, mem: 88, disk: 55, status: "pressure" },
  ],
  storage: [
    { name: "gp3-prometheus", type: "EBS", usedTiB: 1.8, capacityTiB: 4, iops: "within target" },
    { name: "efs-logs", type: "EFS", usedTiB: 6.2, capacityTiB: "elastic", iops: "bursting" },
  ],
};

export const networkMock = {
  regions: [
    { from: "us-east-1", to: "eu-west-1", latencyMs: 89, jitterMs: 4, lossPct: 0.0, throughputGbps: 2.4 },
    { from: "us-east-1", to: "us-west-2", latencyMs: 62, jitterMs: 3, lossPct: 0.0, throughputGbps: 5.0 },
    { from: "edge", to: "us-east-1", latencyMs: 28, jitterMs: 12, lossPct: 0.01, throughputGbps: 18 },
  ],
  ingress: { rps: 12400, bandwidthGbps: 8.2, tlsHandshakeP99Ms: 18 },
  egress: { rps: 9800, bandwidthGbps: 5.1, topDestination: "payments.partner-api.net" },
  dns: { queriesPerSec: 4500, nxdomainRate: 0.02, p99ResolutionMs: 8 },
};
