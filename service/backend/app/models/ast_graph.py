import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class AstGraph(Base):
    __tablename__ = "ast_graph"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo = Column(String(512), nullable=False)
    ref = Column(String(512), nullable=False)
    scanned_files = Column(Integer, nullable=False, default=0)
    parsed_files = Column(Integer, nullable=False, default=0)
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)
    consolidated_graph = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AstGraphIndividual(Base):
    __tablename__ = "ast_graph_individual"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ast_graph_id = Column(UUID(as_uuid=True), ForeignKey("ast_graph.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(2048), nullable=False)
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)
    graph = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AstGraphFunction(Base):
    __tablename__ = "ast_graph_function"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ast_graph_id = Column(UUID(as_uuid=True), ForeignKey("ast_graph.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(2048), nullable=False)
    function_name = Column(String(512), nullable=False)
    start_line = Column(Integer, nullable=True)
    node_count = Column(Integer, nullable=False, default=0)
    edge_count = Column(Integer, nullable=False, default=0)
    graph = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
