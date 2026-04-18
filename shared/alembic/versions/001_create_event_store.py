"""Create Event Store infrastructure tables

Revision ID: 001
Revises:
Create Date: 2026-04-18

This migration creates the foundation for Event Sourcing:
- events table: Immutable log of domain events
- snapshots table: Performance optimization (optional)
- sagas table: Track distributed transactions
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Event Store tables"""

    # Create events table - immutable event log
    # Use Integer (SQLite) which will be BIGINT in PostgreSQL through the ORM
    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(50), nullable=False, unique=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for performance
    op.create_index(
        "idx_events_aggregate", "events", ["aggregate_type", "aggregate_id"]
    )
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_timestamp", "events", ["created_at"])
    op.create_index(
        "idx_events_aggregate_version",
        "events",
        ["aggregate_type", "aggregate_id", "version"],
        unique=True,
    )

    # Create snapshots table - performance optimization
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(50), nullable=False),
        sa.Column("aggregate_state", sa.JSON, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_snapshots_aggregate",
        "snapshots",
        ["aggregate_type", "aggregate_id"],
        unique=True,
    )

    # Create sagas table - distributed transaction tracking
    op.create_table(
        "sagas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("saga_id", sa.String(50), nullable=False, unique=True),
        sa.Column("saga_type", sa.String(100), nullable=False),
        sa.Column("state", sa.JSON, nullable=False),
        sa.Column("compensation_actions", sa.JSON, nullable=True),
        sa.Column("correlation_id", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("idx_sagas_type", "sagas", ["saga_type"])
    op.create_index("idx_sagas_state", "sagas", ["state"])


def downgrade() -> None:
    """Drop Event Store tables"""
    op.drop_table("sagas")
    op.drop_table("snapshots")
    op.drop_table("events")
