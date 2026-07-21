"""Dummy PST knowledge base.

Revision ID: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_base",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_by",
            sa.BigInteger(),
            sa.ForeignKey("dashboard_users.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('DUMMY','VERIFIED')", name="ck_knowledge_base_status"
        ),
        sa.CheckConstraint(
            "length(title) BETWEEN 1 AND 200", name="ck_knowledge_base_title"
        ),
        sa.CheckConstraint(
            "length(content) >= 1 AND length(content) <= 20000",
            name="ck_knowledge_base_content",
        ),
        sa.CheckConstraint(
            "source_url IS NULL OR source_url ~ '^https://([a-z0-9-]+\\.)*bps\\.go\\.id(/|$)'",
            name="ck_knowledge_base_source_url",
        ),
    )
    table = sa.table(
        "knowledge_base",
        sa.column("key", sa.String),
        sa.column("title", sa.String),
        sa.column("content", sa.Text),
        sa.column("source_url", sa.Text),
        sa.column("status", sa.String),
    )
    op.bulk_insert(
        table,
        [
            {
                "key": "dummy.pst.services",
                "title": "Layanan PST — BELUM DIVERIFIKASI",
                "content": "DUMMY: Daftar layanan PST masih berupa placeholder dan belum diverifikasi.",
                "source_url": None,
                "status": "DUMMY",
            },
            {
                "key": "dummy.pst.hours",
                "title": "Jam layanan — BELUM DIVERIFIKASI",
                "content": "DUMMY: Jam layanan masih berupa placeholder dan belum diverifikasi.",
                "source_url": None,
                "status": "DUMMY",
            },
            {
                "key": "dummy.pst.consultation",
                "title": "Konsultasi/rekomendasi — BELUM DIVERIFIKASI",
                "content": "DUMMY: Untuk konsultasi atau rekomendasi, gunakan Buku Tamu. Informasi ini belum diverifikasi.",
                "source_url": "https://s.bps.go.id/tamu1306",
                "status": "DUMMY",
            },
        ],
    )


def downgrade():
    op.drop_table("knowledge_base")
