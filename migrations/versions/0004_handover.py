"""Durable handover state and generation fencing.

Revision ID: 0004
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

GUESTBOOK_URL = "https://s.bps.go.id/tamu1306"


def upgrade():
    op.create_table(
        "handovers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_phone", sa.String(16), nullable=False),
        sa.Column(
            "state", sa.String(20), nullable=False, server_default="HANDOVER_PENDING"
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("owner_id", sa.String(64)),
        sa.Column("generation", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True)),
        sa.Column("fallback_url", sa.String(64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("state IN ('BOT_ACTIVE','HANDOVER_PENDING','ADMIN_ACTIVE')"),
        sa.CheckConstraint(
            "status IN ('PENDING','ACTIVE','RESOLVED','FAILED','EXPIRED')"
        ),
        sa.CheckConstraint(
            "fallback_url IS NULL OR fallback_url = 'https://s.bps.go.id/tamu1306'"
        ),
        sa.CheckConstraint("generation >= 0"),
        sa.CheckConstraint("(status = 'ACTIVE') = (owner_id IS NOT NULL)"),
    )
    op.create_index(
        "uq_handovers_open_user",
        "handovers",
        ["user_phone"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','ACTIVE')"),
    )
    op.create_index(
        "uq_handovers_active_owner",
        "handovers",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_handovers_due",
        "handovers",
        ["deadline_at"],
        postgresql_where=sa.text("status = 'PENDING' AND deadline_at IS NOT NULL"),
    )


def downgrade():
    op.drop_table("handovers")
