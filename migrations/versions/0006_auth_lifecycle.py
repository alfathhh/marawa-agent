"""Dashboard authentication lifecycle state.

Revision ID: 0006
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dashboard_users",
        sa.Column(
            "session_version", sa.BigInteger(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "dashboard_users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_check_constraint(
        "ck_dashboard_users_session_version_positive",
        "dashboard_users",
        "session_version >= 1",
    )


def downgrade():
    op.drop_constraint(
        "ck_dashboard_users_session_version_positive",
        "dashboard_users",
        type_="check",
    )
    op.drop_column("dashboard_users", "must_change_password")
    op.drop_column("dashboard_users", "session_version")
