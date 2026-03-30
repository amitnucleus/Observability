import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from typing import Optional
from graph.engine import get_graph
from graph.types import Scope
from graph.type_layer import get_legal_connections_summary
from rca.traversal import trace, get_anomalies

# ── GraphQL types ──────────────────────────────────────────────

@strawberry.type
class GraphNode:
    id:          str
    layer:       int
    layer_name:  str
    event_type:  str
    severity:    str
    weight:      float
    event_count: int
    node_type:   str

@strawberry.type
class GraphEdge:
    source:              str
    target:              str
    co_occurrence_count: int
    weight:              float
    edge_type:           str
    is_legal:            bool

@strawberry.type
class RCACandidate:
    node_id:     str
    layer:       int
    layer_name:  str
    severity:    str
    weight:      float
    path_weight: float
    event_count: int
    depth:       int

@strawberry.type
class RCAResult:
    fault_node:   str
    candidates:   list[RCACandidate]
    blast_radius: list[str]

@strawberry.type
class GraphStats:
    nodes:    int
    edges:    int
    timeline: int

@strawberry.type
class TypeLayerConnection:
    source_type: str
    target_type: str
    edge_types:  list[str]

# ── Queries ────────────────────────────────────────────────────

@strawberry.type
class Query:

    @strawberry.field
    def nodes(self, scope: Optional[str] = None) -> list[GraphNode]:
        g = get_graph()

        if scope:
            try:
                s = Scope(scope.upper())
            except ValueError:
                s = Scope.DEV
            raw_nodes = g.get_scoped_nodes(s)
        else:
            raw_nodes = g.get_all_nodes()

        return [
            GraphNode(
                id          = d["id"],
                layer       = d.get("layer", 0),
                layer_name  = d.get("layer_name", ""),
                event_type  = d.get("event_type", ""),
                severity    = d.get("severity", "INFO"),
                weight      = round(d.get("observation_weight", 0), 3),
                event_count = d.get("event_count", 0),
                node_type   = d.get("node_type", "UNKNOWN"),
            )
            for d in raw_nodes
        ]

    @strawberry.field
    def edges(self, scope: Optional[str] = None) -> list[GraphEdge]:
        g = get_graph()

        if scope:
            try:
                s = Scope(scope.upper())
            except ValueError:
                s = Scope.DEV
            raw_edges = g.get_scoped_edges(s)
        else:
            raw_edges = g.get_all_edges()

        return [
            GraphEdge(
                source              = e["source"],
                target              = e["target"],
                co_occurrence_count = e.get("co_occurrence_count", 0),
                weight              = round(e.get("weight", 0), 3),
                edge_type           = e.get("edge_type", "CO_OCCURS"),
                is_legal            = e.get("is_legal", True),
            )
            for e in raw_edges
        ]

    @strawberry.field
    def rca(self, node_id: str, max_depth: Optional[int] = 6) -> RCAResult:
        result = trace(node_id, max_depth or 6)
        return RCAResult(
            fault_node   = result["fault_node"],
            blast_radius = result["blast_radius"],
            candidates   = [RCACandidate(**c) for c in result["candidates"]],
        )

    @strawberry.field
    def anomalies(self, threshold: Optional[float] = 5.0) -> list[GraphNode]:
        items = get_anomalies(threshold or 5.0)
        g = get_graph()
        result = []
        for a in items:
            nid  = a["node_id"]
            data = g.G.nodes.get(nid, {})
            result.append(GraphNode(
                id          = nid,
                layer       = data.get("layer", 0),
                layer_name  = a["layer_name"],
                event_type  = data.get("event_type", ""),
                severity    = a["severity"],
                weight      = a["weight"],
                event_count = a["event_count"],
                node_type   = data.get("node_type", "UNKNOWN"),
            ))
        return result

    @strawberry.field
    def stats(self) -> GraphStats:
        s = get_graph().stats()
        return GraphStats(**s)

    @strawberry.field
    def type_layer(self) -> list[TypeLayerConnection]:
        connections = get_legal_connections_summary()
        return [
            TypeLayerConnection(
                source_type = c["source_type"],
                target_type = c["target_type"],
                edge_types  = c["edge_types"],
            )
            for c in connections
        ]

    @strawberry.field
    def available_scopes(self) -> list[str]:
        return [s.value for s in Scope]

    @strawberry.field
    def available_node_types(self) -> list[str]:
        from graph.types import NodeType
        return [nt.value for nt in NodeType]

    @strawberry.field
    def available_edge_types(self) -> list[str]:
        from graph.types import EdgeType
        return [et.value for et in EdgeType]


# ── App ────────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query)

app = FastAPI(title="PNOG API")
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok", **get_graph().stats()}
