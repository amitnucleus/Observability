"""
Type Layer — the schema of the PNOG graph.

Defines:
  1. Legal connections between NodeTypes (what CAN connect to what)
  2. EdgeType inference (given two NodeTypes, what EdgeType applies)
  3. Minimization operators (how each NodeType behaves per Scope)

This is the "class hierarchy" from the Abstract Graph model.
Connections not defined here are structurally invalid.
"""

from __future__ import annotations

from .types import EdgeType, MinimizationAction, NodeType, Scope


# ---------------------------------------------------------------------------
#  Legal connections: (source_NodeType, target_NodeType) → EdgeType
#
#  If a pair is NOT in this map, that edge is structurally invalid.
#  Multiple EdgeTypes per pair are allowed (list).
# ---------------------------------------------------------------------------

LEGAL_CONNECTIONS: dict[tuple[NodeType, NodeType], list[EdgeType]] = {
    # L0 Network → L1 Application
    (NodeType.NETWORK_REQUEST, NodeType.SERVICE_CALL):   [EdgeType.TRIGGERS],
    (NodeType.NETWORK_REQUEST, NodeType.NETWORK_REQUEST): [EdgeType.CO_OCCURS],

    # L1 Application → various
    (NodeType.SERVICE_CALL, NodeType.SERVICE_CALL):      [EdgeType.CALLS, EdgeType.CO_OCCURS],
    (NodeType.SERVICE_CALL, NodeType.DB_WRITER):         [EdgeType.CALLS, EdgeType.WRITES],
    (NodeType.SERVICE_CALL, NodeType.CACHE_OP):          [EdgeType.CALLS, EdgeType.READS_FROM],
    (NodeType.SERVICE_CALL, NodeType.LOG_EMITTER):       [EdgeType.EMITS_TO],
    (NodeType.SERVICE_CALL, NodeType.NETWORK_REQUEST):   [EdgeType.CO_OCCURS],
    (NodeType.SERVICE_CALL, NodeType.FRONTEND_ERROR):    [EdgeType.CO_OCCURS],

    # L2 Pod events
    (NodeType.POD_EVENT, NodeType.SERVICE_CALL):         [EdgeType.CO_OCCURS, EdgeType.TRIGGERS],
    (NodeType.POD_EVENT, NodeType.POD_EVENT):            [EdgeType.CO_OCCURS],
    (NodeType.POD_EVENT, NodeType.DB_WRITER):            [EdgeType.CO_OCCURS],
    (NodeType.POD_EVENT, NodeType.RESOURCE_METRIC):      [EdgeType.CO_OCCURS],

    # L3 Database
    (NodeType.DB_WRITER, NodeType.DB_WRITER):            [EdgeType.CO_OCCURS],
    (NodeType.DB_WRITER, NodeType.SERVICE_CALL):         [EdgeType.CO_OCCURS],
    (NodeType.DB_WRITER, NodeType.CACHE_OP):             [EdgeType.CO_OCCURS],

    # L4 Cache
    (NodeType.CACHE_OP, NodeType.CACHE_OP):              [EdgeType.CO_OCCURS],
    (NodeType.CACHE_OP, NodeType.SERVICE_CALL):          [EdgeType.CO_OCCURS],
    (NodeType.CACHE_OP, NodeType.DB_WRITER):             [EdgeType.CO_OCCURS],

    # L5 Git releases → cascading effects
    (NodeType.RELEASE_SNAPSHOT, NodeType.POD_EVENT):     [EdgeType.TRIGGERS],
    (NodeType.RELEASE_SNAPSHOT, NodeType.SERVICE_CALL):  [EdgeType.TRIGGERS],
    (NodeType.RELEASE_SNAPSHOT, NodeType.RELEASE_SNAPSHOT): [EdgeType.CO_OCCURS],

    # L6 Frontend
    (NodeType.FRONTEND_ERROR, NodeType.NETWORK_REQUEST): [EdgeType.TRIGGERS, EdgeType.CO_OCCURS],
    (NodeType.FRONTEND_ERROR, NodeType.SERVICE_CALL):    [EdgeType.CO_OCCURS],
    (NodeType.FRONTEND_ERROR, NodeType.FRONTEND_ERROR):  [EdgeType.CO_OCCURS],

    # L7 Metrics
    (NodeType.RESOURCE_METRIC, NodeType.POD_EVENT):      [EdgeType.CO_OCCURS],
    (NodeType.RESOURCE_METRIC, NodeType.SERVICE_CALL):   [EdgeType.CO_OCCURS],
    (NodeType.RESOURCE_METRIC, NodeType.DB_WRITER):      [EdgeType.CO_OCCURS],
    (NodeType.RESOURCE_METRIC, NodeType.RESOURCE_METRIC): [EdgeType.CO_OCCURS],

    # Collapsed / abstract types
    (NodeType.SERVICE, NodeType.DATABASE):               [EdgeType.DEPENDS_ON],
    (NodeType.SERVICE, NodeType.CACHE):                  [EdgeType.DEPENDS_ON],
    (NodeType.SERVICE, NodeType.QUEUE):                  [EdgeType.DEPENDS_ON],
    (NodeType.SERVICE, NodeType.SERVICE):                [EdgeType.DEPENDS_ON, EdgeType.CALLS],

    # Code-structure types (for AST bridge)
    (NodeType.FUNCTION, NodeType.FUNCTION):              [EdgeType.CALLS],
    (NodeType.FUNCTION, NodeType.CONDITIONAL):           [EdgeType.CALLS],
    (NodeType.FUNCTION, NodeType.DB_WRITER):             [EdgeType.CALLS, EdgeType.WRITES],
    (NodeType.FUNCTION, NodeType.LOG_EMITTER):           [EdgeType.CALLS, EdgeType.EMITS_TO],
    (NodeType.CONDITIONAL, NodeType.FUNCTION):           [EdgeType.CALLS],
    (NodeType.CONDITIONAL, NodeType.DB_WRITER):          [EdgeType.CALLS],
    (NodeType.LOG_EMITTER, NodeType.QUEUE):              [EdgeType.EMITS_TO],
}


def is_legal_connection(source_type: NodeType, target_type: NodeType) -> bool:
    """Check whether an edge between these two NodeTypes is permitted."""
    return (source_type, target_type) in LEGAL_CONNECTIONS


def infer_edge_type(source_type: NodeType, target_type: NodeType) -> EdgeType:
    """
    Given two NodeTypes, return the most specific EdgeType.

    If the pair is legal, return the first (most specific) EdgeType.
    If not legal, return CO_OCCURS as a fallback (soft enforcement).
    """
    edge_types = LEGAL_CONNECTIONS.get((source_type, target_type))
    if edge_types:
        return edge_types[0]
    # Also check the reverse direction
    edge_types_rev = LEGAL_CONNECTIONS.get((target_type, source_type))
    if edge_types_rev:
        return edge_types_rev[0]
    return EdgeType.CO_OCCURS


# ---------------------------------------------------------------------------
#  Minimization operators — per-NodeType, per-Scope behavior
#
#  Each NodeType defines how it behaves when the graph is viewed at a
#  given Scope. This is the "method on the class" from the OOP analogy.
# ---------------------------------------------------------------------------

# collapse_to: when action is COLLAPSE, what NodeType does it become?
_COLLAPSE_MAP: dict[NodeType, NodeType] = {
    NodeType.NETWORK_REQUEST:  NodeType.SERVICE,
    NodeType.SERVICE_CALL:     NodeType.SERVICE,
    NodeType.POD_EVENT:        NodeType.SERVICE,
    NodeType.DB_WRITER:        NodeType.DATABASE,
    NodeType.CACHE_OP:         NodeType.CACHE,
    NodeType.RELEASE_SNAPSHOT: NodeType.SERVICE,
    NodeType.FRONTEND_ERROR:   NodeType.SERVICE,
    NodeType.RESOURCE_METRIC:  NodeType.SERVICE,
    NodeType.FUNCTION:         NodeType.SERVICE,
    NodeType.CONDITIONAL:      NodeType.SERVICE,
    NodeType.LOG_EMITTER:      NodeType.SERVICE,
}

MINIMIZATION_OPERATORS: dict[NodeType, dict[Scope, MinimizationAction]] = {
    NodeType.NETWORK_REQUEST: {
        Scope.SRE:         MinimizationAction.KEEP,      # SRE sees network requests
        Scope.DEV:         MinimizationAction.KEEP,      # DEV sees full detail
        Scope.SECURITY:    MinimizationAction.KEEP,      # SEC sees all network activity
        Scope.THIRD_PARTY: MinimizationAction.COLLAPSE,  # 3rd party sees SERVICE
    },
    NodeType.SERVICE_CALL: {
        Scope.SRE:         MinimizationAction.COLLAPSE,  # SRE sees SERVICE, not individual calls
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.COLLAPSE,
        Scope.THIRD_PARTY: MinimizationAction.COLLAPSE,
    },
    NodeType.POD_EVENT: {
        Scope.SRE:         MinimizationAction.KEEP,      # SRE cares about pod events
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.EXCLUDE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.DB_WRITER: {
        Scope.SRE:         MinimizationAction.COLLAPSE,  # SRE sees DATABASE
        Scope.DEV:         MinimizationAction.KEEP,      # DEV sees query patterns
        Scope.SECURITY:    MinimizationAction.KEEP,      # SEC flags external DB access
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.CACHE_OP: {
        Scope.SRE:         MinimizationAction.COLLAPSE,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.EXCLUDE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.RELEASE_SNAPSHOT: {
        Scope.SRE:         MinimizationAction.KEEP,      # SRE tracks deployments
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.KEEP,      # SEC tracks code changes
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.FRONTEND_ERROR: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.KEEP,
        Scope.THIRD_PARTY: MinimizationAction.COLLAPSE,
    },
    NodeType.RESOURCE_METRIC: {
        Scope.SRE:         MinimizationAction.KEEP,      # SRE lives here
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.EXCLUDE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    # Collapsed types are always kept (they are the result of collapsing)
    NodeType.SERVICE: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.KEEP,
        Scope.THIRD_PARTY: MinimizationAction.KEEP,
    },
    NodeType.DATABASE: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.KEEP,
        Scope.THIRD_PARTY: MinimizationAction.KEEP,
    },
    NodeType.CACHE: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.EXCLUDE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.QUEUE: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.EXCLUDE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    # Code-structure types
    NodeType.FUNCTION: {
        Scope.SRE:         MinimizationAction.COLLAPSE,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.COLLAPSE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.CONDITIONAL: {
        Scope.SRE:         MinimizationAction.COLLAPSE,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.COLLAPSE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.LOG_EMITTER: {
        Scope.SRE:         MinimizationAction.COLLAPSE,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.COLLAPSE,
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
    NodeType.UNKNOWN: {
        Scope.SRE:         MinimizationAction.KEEP,
        Scope.DEV:         MinimizationAction.KEEP,
        Scope.SECURITY:    MinimizationAction.KEEP,      # unknowns are flagged
        Scope.THIRD_PARTY: MinimizationAction.EXCLUDE,
    },
}


def get_minimization_action(node_type: NodeType, scope: Scope) -> MinimizationAction:
    """Return what should happen to a node of this type at this scope."""
    ops = MINIMIZATION_OPERATORS.get(node_type)
    if ops is None:
        return MinimizationAction.KEEP
    return ops.get(scope, MinimizationAction.KEEP)


def get_collapse_target(node_type: NodeType) -> NodeType:
    """When a NodeType is collapsed, what does it become?"""
    return _COLLAPSE_MAP.get(node_type, NodeType.SERVICE)


def get_legal_connections_summary() -> list[dict]:
    """Return a serializable summary of all legal connections."""
    result = []
    for (src, tgt), edge_types in LEGAL_CONNECTIONS.items():
        result.append({
            "source_type": src.value,
            "target_type": tgt.value,
            "edge_types": [et.value for et in edge_types],
        })
    return result
