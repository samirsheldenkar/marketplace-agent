"""Database models."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Listing(Base):
    """Listing model for storing item information and generated drafts."""

    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'clarification', 'completed', 'failed')",
            name="check_listing_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    status = Column(String(20), default="pending", nullable=False)

    # Item attributes
    item_type = Column(String(100))
    item_description = Column(Text)
    brand = Column(String(100))
    model_name = Column(String(200))
    size = Column(String(50))
    color = Column(String(100))
    condition = Column(String(20))
    condition_notes = Column(Text)
    confidence = Column(Float)
    accessories_included = Column(JSONB, default=list)

    # Pricing
    suggested_price = Column(Numeric(10, 2))
    preferred_platform = Column(String(10))
    platform_reasoning = Column(Text)

    # Generated content
    title = Column(String(200))
    description = Column(Text)
    listing_draft = Column(JSONB)

    # Full state snapshot
    raw_state = Column(JSONB)

    # Image paths
    image_paths = Column(JSONB, default=list)

    # Relationships
    scrape_runs = relationship(
        "ScrapeRun", back_populates="listing", cascade="all, delete-orphan"
    )
    agent_runs = relationship(
        "AgentRun", back_populates="listing", cascade="all, delete-orphan"
    )


class ScrapeRun(Base):
    """Scrape run model for tracking marketplace queries."""

    __tablename__ = "scrape_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    source = Column(String(10), nullable=False)  # "ebay" or "vinted"
    query_string = Column(Text, nullable=False)
    stats = Column(JSONB)
    raw_items = Column(JSONB)
    item_count = Column(Integer)
    duration_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    listing = relationship("Listing", back_populates="scrape_runs")


class AgentRun(Base):
    """Agent run model for audit logging."""

    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_name = Column(String(50), nullable=False)
    started_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="running")
    input_summary = Column(JSONB)
    output_summary = Column(JSONB)
    error_message = Column(Text)
    llm_model_used = Column(String(100))
    token_usage = Column(JSONB)

    # Relationships
    listing = relationship("Listing", back_populates="agent_runs")
