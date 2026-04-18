from typing import Any
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base: Any = declarative_base()


class EventModel(Base):
    """Event Store record"""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), nullable=False, unique=True)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    event_metadata = Column(JSON, nullable=True, name="metadata")
    created_at = Column(DateTime(timezone=False), default=datetime.now, nullable=False)
