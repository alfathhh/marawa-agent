"""Inbound worker leases.

Revision ID: 0003
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("inbound_events", sa.Column("claim_token", sa.String(64)))
    op.add_column(
        "inbound_events", sa.Column("lease_until", sa.DateTime(timezone=True))
    )
    op.add_column("inbound_events", sa.Column("last_error", sa.String(128)))
    op.create_index(
        "ix_inbound_ready", "inbound_events", ["status", "available_at", "created_at"]
    )


def downgrade():
    op.drop_index("ix_inbound_ready", table_name="inbound_events")
    op.drop_column("inbound_events", "last_error")
    op.drop_column("inbound_events", "lease_until")
    op.drop_column("inbound_events", "claim_token")
