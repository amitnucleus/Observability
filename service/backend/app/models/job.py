import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename   = Column(String(255), nullable=False)
    status     = Column(String(50), default="pending")   # pending | processing | done | failed
    result     = Column(Text, nullable=True)
    file_size  = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
