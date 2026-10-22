from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class RawItem(BaseModel):
    """Canonical shape every connector must emit."""
    item_id: str
    platform: str
    native_id: str
    author_hash: str | None = None
    text: str = ""
    media_urls: list[str] = Field(default_factory=list)
    timestamp: datetime
    geo_hint: dict[str, Any] | None = None
    tagged_departments: list[str] = Field(default_factory=list)
    engagement: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class Base(DeclarativeBase):
    pass


class SourceItemRow(Base):
    __tablename__ = "source_items"

    item_id = Column(String, primary_key=True)
    platform = Column(String, index=True, nullable=False)
    native_id = Column(String, index=True, nullable=False)
    author_hash = Column(String)
    text = Column(Text)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    geo_hint = Column(JSON)
    tagged_departments = Column(JSON)
    engagement = Column(JSON)
    
    link = Column(String)         # <--- MUST BE HERE
    media_urls = Column(JSON)     # <--- MUST BE HERE
    
    raw = Column(JSON)
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow)


def make_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True, future=True)


def init_db(db_url: str):
    engine = make_engine(db_url)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)