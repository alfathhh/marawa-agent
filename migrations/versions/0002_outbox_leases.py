"""Outbox worker leases.

Revision ID: 0002
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("outbound_messages", sa.Column("claim_token", sa.String(64)))
    op.add_column(
        "outbound_messages", sa.Column("lease_until", sa.DateTime(timezone=True))
    )
    op.add_column("outbound_messages", sa.Column("last_error", sa.String(128)))
    op.create_index(
        "ix_outbound_ready",
        "outbound_messages",
        ["status", "available_at", "created_at"],
    )


def downgrade():
    op.drop_index("ix_outbound_ready", table_name="outbound_messages")
    op.drop_column("outbound_messages", "last_error")
    op.drop_column("outbound_messages", "lease_until")
    op.drop_column("outbound_messages", "claim_token")
