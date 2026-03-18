"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-03-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create listings table
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        # Item attributes
        sa.Column("item_type", sa.String(100)),
        sa.Column("item_description", sa.Text()),
        sa.Column("brand", sa.String(100)),
        sa.Column("model_name", sa.String(200)),
        sa.Column("size", sa.String(50)),
        sa.Column("color", sa.String(100)),
        sa.Column("condition", sa.String(20)),
        sa.Column("condition_notes", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("accessories_included", postgresql.JSONB(), default=list),
        # Pricing
        sa.Column("suggested_price", sa.Numeric(10, 2)),
        sa.Column("preferred_platform", sa.String(10)),
        sa.Column("platform_reasoning", sa.Text()),
        # Generated content
        sa.Column("title", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("listing_draft", postgresql.JSONB()),
        # Full state snapshot
        sa.Column("raw_state", postgresql.JSONB()),
        # Image paths
        sa.Column("image_paths", postgresql.JSONB(), default=list),
    )

    op.create_index("idx_listings_status", "listings", ["status"])
    op.create_index("idx_listings_created_at", "listings", ["created_at"])

    # Create scrape_runs table
    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("query_string", sa.Text(), nullable=False),
        sa.Column("stats", postgresql.JSONB()),
        sa.Column("raw_items", postgresql.JSONB()),
        sa.Column("item_count", sa.Integer()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("idx_scrape_runs_listing_id", "scrape_runs", ["listing_id"])

    # Create agent_runs table
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_name", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), default="running"),
        sa.Column("input_summary", postgresql.JSONB()),
        sa.Column("output_summary", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("llm_model_used", sa.String(100)),
        sa.Column("token_usage", postgresql.JSONB()),
    )

    op.create_index("idx_agent_runs_listing_id", "agent_runs", ["listing_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("agent_runs")
    op.drop_table("scrape_runs")
    op.drop_table("listings")
