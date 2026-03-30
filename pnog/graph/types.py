"""
Abstract Graph Type System for PNOG.

Defines the four-element vocabulary from the Abstract Graph model:
  - NodeType: class templates for graph nodes
  - EdgeType: class templates for graph edges
  - Scope: roles that receive different graph views
  - MinimizationAction: what happens to a NodeType at a given scope
"""

from enum import Enum


# ---------------------------------------------------------------------------
#  NodeType — the "classes" that all graph nodes belong to
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    """
    Every node in the PNOG graph is an instance of exactly one NodeType.

    Runtime layer types (from the 8 log layers):
    """
    NETWORK_REQUEST   = "NETWORK_REQUEST"    # L0 — Nginx / reverse-proxy
    SERVICE_CALL      = "SERVICE_CALL"       # L1 — FastAPI / application
    POD_EVENT         = "POD_EVENT"          # L2 — Docker / K8s
    DB_WRITER         = "DB_WRITER"          # L3 — Postgres / database ops
    CACHE_OP          = "CACHE_OP"           # L4 — Redis / cache ops
    RELEASE_SNAPSHOT  = "RELEASE_SNAPSHOT"   # L5 — Git webhook
    FRONTEND_ERROR    = "FRONTEND_ERROR"     # L6 — Browser / Sentry
    RESOURCE_METRIC   = "RESOURCE_METRIC"    # L7 — Prometheus / metrics

    # Abstract / collapsed types (used by minimization operators)
    SERVICE           = "SERVICE"            # collapsed parent for SRE view
    DATABASE          = "DATABASE"           # collapsed infra node
    CACHE             = "CACHE"              # collapsed infra node
    QUEUE             = "QUEUE"              # collapsed infra node

    # Code-structure types (from AST analysis — future bridge)
    FUNCTION          = "FUNCTION"
    CONDITIONAL       = "CONDITIONAL"
    LOG_EMITTER       = "LOG_EMITTER"

    UNKNOWN           = "UNKNOWN"


# ---------------------------------------------------------------------------
#  EdgeType — the "classes" that all graph edges belong to
# ---------------------------------------------------------------------------

class EdgeType(str, Enum):
    """
    Every edge in the PNOG graph is an instance of exactly one EdgeType.
    """
    CALLS       = "CALLS"        # function invocation
    QUERIES     = "QUERIES"      # database read
    WRITES      = "WRITES"       # database / cache write
    EMITS_TO    = "EMITS_TO"     # event emission (Kafka, log)
    READS_FROM  = "READS_FROM"   # cache / queue read
    TRIGGERS    = "TRIGGERS"     # causal trigger (request → service call)
    DEPENDS_ON  = "DEPENDS_ON"   # runtime dependency
    CO_OCCURS   = "CO_OCCURS"    # temporal co-occurrence (default)

    UNKNOWN     = "UNKNOWN"


# ---------------------------------------------------------------------------
#  Scope — the roles that receive minimized graph views
# ---------------------------------------------------------------------------

class Scope(str, Enum):
    """
    Each scope sees a different projection of the same underlying graph.
    """
    SRE       = "SRE"        # infrastructure-level view
    DEV       = "DEV"        # full developer detail
    SECURITY  = "SECURITY"   # external connections + anomalies
    THIRD_PARTY = "THIRD_PARTY"  # topology only


# ---------------------------------------------------------------------------
#  MinimizationAction — what happens to a node at a given scope
# ---------------------------------------------------------------------------

class MinimizationAction(str, Enum):
    """
    The result of applying a minimization operator to a NodeType at a scope.
    """
    KEEP     = "KEEP"      # node stays as-is
    COLLAPSE = "COLLAPSE"  # node collapses into its parent type
    EXCLUDE  = "EXCLUDE"   # node is removed from the graph view
