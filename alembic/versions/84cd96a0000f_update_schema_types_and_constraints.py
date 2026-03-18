"""Update schema types and constraints

Revision ID: 84cd96a0000f
Revises: 001
Create Date: 2026-03-17 15:30:52.614207

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "84cd96a0000f"
down_revision: str | Sequence[str] | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change columns to JSONB
    op.execute(
        "ALTER TABLE listings ALTER COLUMN accessories_included TYPE JSONB USING accessories_included::jsonb"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN listing_draft TYPE JSONB USING listing_draft::jsonb"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN raw_state TYPE JSONB USING raw_state::jsonb"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN image_paths TYPE JSONB USING image_paths::jsonb"
    )

    op.execute(
        "ALTER TABLE scrape_runs ALTER COLUMN stats TYPE JSONB USING stats::jsonb"
    )
    op.execute(
        "ALTER TABLE scrape_runs ALTER COLUMN raw_items TYPE JSONB USING raw_items::jsonb"
    )

    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN input_summary TYPE JSONB USING input_summary::jsonb"
    )
    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN output_summary TYPE JSONB USING output_summary::jsonb"
    )
    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN token_usage TYPE JSONB USING token_usage::jsonb"
    )

    # Change Float to Numeric(10,2)
    op.execute("ALTER TABLE listings ALTER COLUMN suggested_price TYPE NUMERIC(10, 2)")

    # Add CheckConstraint
    op.create_check_constraint(
        "check_listing_status",
        "listings",
        "status IN ('pending', 'processing', 'clarification', 'completed', 'failed')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraint
    op.drop_constraint("check_listing_status", "listings", type_="check")

    # Revert Numeric to Float
    op.execute("ALTER TABLE listings ALTER COLUMN suggested_price TYPE REAL")

    # Revert JSONB to JSON
    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN token_usage TYPE JSON USING token_usage::json"
    )
    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN output_summary TYPE JSON USING output_summary::json"
    )
    op.execute(
        "ALTER TABLE agent_runs ALTER COLUMN input_summary TYPE JSON USING input_summary::json"
    )

    op.execute(
        "ALTER TABLE scrape_runs ALTER COLUMN raw_items TYPE JSON USING raw_items::json"
    )
    op.execute("ALTER TABLE scrape_runs ALTER COLUMN stats TYPE JSON USING stats::json")

    op.execute(
        "ALTER TABLE listings ALTER COLUMN image_paths TYPE JSON USING image_paths::json"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN raw_state TYPE JSON USING raw_state::json"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN listing_draft TYPE JSON USING listing_draft::json"
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN accessories_included TYPE JSON USING accessories_included::json"
    )
