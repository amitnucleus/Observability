from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base

# Single-row table: id must always be 1.
SINGLETON_ID = 1


class GitConfigRow(Base):
    __tablename__ = "git_config"

    id = Column(Integer, primary_key=True)
    repo = Column(String(1024), nullable=False)
    ref = Column(String(512), nullable=False)
    github_token = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
