# PNOG — Pipeline Node Operation Graph

Passive · Probabilistic · Multi-Layer Observability & Root Cause Analysis

## Quick Start

```bash
# 1. Clone and enter
git clone <repo> && cd pnog

# 2. Start everything
docker compose up --build

# 3. Open interfaces
# Service:      http://localhost
# Frontend:     http://localhost:3000
# Kafka UI:     http://localhost:8080
# Prometheus:   http://localhost:9090
# PNOG API:     http://localhost:8100/graphql
# PNOG UI:      http://localhost:3002
```

## Structure

```
pnog/
├── docker-compose.yml       # Full stack orchestration
├── .env                     # Environment variables
├── service/
│   ├── nginx/               # Reverse proxy + JSON access logs
│   ├── backend/             # FastAPI + Celery + Kafka publisher
│   └── frontend/            # Next.js + Sentry
├── infra/
│   ├── kafka/               # Topic definitions
│   ├── fluentd/             # Log routing → Kafka
│   ├── prometheus/          # Metrics scraping
│   └── fault_injection/     # Error playbook scripts
└── pnog/
    ├── consumer/            # Kafka consumer + event router
    ├── parsers/             # One parser per layer (L0-L7)
    ├── graph/               # NetworkX engine + W(u,v,t)
    ├── rca/                 # Traversal + blast radius
    ├── api/                 # GraphQL API (Strawberry)
    ├── ui/                  # Real-time graph UI (vis.js)
    └── tests/               # Fault scenario tests
```

## The 8 Log Layers

| Layer | Source       | Kafka Topic        | PNOG Node Type       |
|-------|--------------|--------------------|----------------------|
| L0    | Nginx        | net.requests       | NetworkRequest       |
| L1    | FastAPI      | app.events         | ServiceCall          |
| L2    | Docker/K8s   | pod.logs           | PodEvent             |
| L3    | Postgres     | db.queries         | DBQuery              |
| L4    | Redis        | cache.events       | CacheEvent           |
| L5    | Git webhook  | git.releases       | ReleaseSnapshot      |
| L6    | Browser      | frontend.errors    | FrontendError        |
| L7    | Prometheus   | metrics.resources  | ResourceMetric       |

## W(u,v,t) — The Weight Formula

```
W(u,v,t) = Σ co(u,v,τ) × e^(−λ(t−τ))
```

- `u, v` — node pair
- `co(u,v,τ)` — co-occurrence at time τ
- `λ` — recency decay rate (default 0.1)
- `t−τ` — time elapsed since event

## Fault Injection

```bash
# DB connection pool exhaustion
python infra/fault_injection/db_pool_exhaust.py

# Cache miss storm
python infra/fault_injection/cache_miss_storm.py

# Simulate a bad git release
curl -X POST http://localhost:8001/webhook/simulate?ref=refs/heads/bad-release
```

## GraphQL Queries

```graphql
# Get all anomalous nodes
query { anomalies { id layerName weight severity } }

# Trace root cause from a fault node
query { rca(nodeId: "postgres:jobs:UPDATE") { candidates { nodeId weight depth } blastRadius } }

# Full graph snapshot
query { nodes { id layer weight } edges { source target weight } }
```
