import os

import pytest
from sqlalchemy import create_engine, text

from operational.dashboard_backend import DashboardBackend

DATABASE_URL = os.getenv(
    "MARAWA_TEST_DATABASE_URL",
    "postgresql+psycopg://marawa:marawa_test_only@127.0.0.1:55432/marawa_test",
)


@pytest.fixture
def connection():
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            yield conn
            transaction.rollback()
    except Exception as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")
    finally:
        engine.dispose()


def test_list_knowledge_returns_seeded_dummy_entries(connection):
    rows = DashboardBackend(connection).list_knowledge()

    assert {row["key"] for row in rows} >= {
        "dummy.pst.services",
        "dummy.pst.hours",
        "dummy.pst.consultation",
    }
    assert all(row["status"] == "DUMMY" for row in rows)
    consultation = next(row for row in rows if row["key"] == "dummy.pst.consultation")
    assert consultation["source_url"] == "https://s.bps.go.id/tamu1306"


def test_update_knowledge_persists_closed_schema_and_audits(connection):
    backend = DashboardBackend(connection)
    actor_id = connection.execute(
        text("""INSERT INTO dashboard_users (username,password_hash,role,must_change_password)
                VALUES ('kb.admin','hash','superadmin',false) RETURNING id""")
    ).scalar_one()

    row = backend.update_knowledge(
        "dummy.pst.services",
        {
            "title": "Layanan PST (DUMMY)",
            "content": "Konten placeholder yang belum diverifikasi.",
            "source_url": None,
            "status": "DUMMY",
        },
        actor_id=actor_id,
    )

    assert row["updated_by"] == actor_id
    assert row["content"] == "Konten placeholder yang belum diverifikasi."
    assert (
        connection.execute(
            text(
                "SELECT count(*) FROM audit_log WHERE action='knowledge.update' AND target='dummy.pst.services'"
            )
        ).scalar_one()
        == 1
    )


@pytest.mark.parametrize(
    "body",
    [
        {
            "title": "x",
            "content": "x",
            "source_url": None,
            "status": "DUMMY",
            "extra": 1,
        },
        {"title": "x" * 201, "content": "x", "source_url": None, "status": "DUMMY"},
        {"title": "x", "content": "x" * 20001, "source_url": None, "status": "DUMMY"},
        {
            "title": "x",
            "content": "x",
            "source_url": "http://bps.go.id/x",
            "status": "DUMMY",
        },
        {
            "title": "x",
            "content": "x",
            "source_url": "https://evil.example/x",
            "status": "VERIFIED",
        },
        {"title": "x", "content": "x", "source_url": None, "status": "PUBLISHED"},
    ],
)
def test_update_knowledge_rejects_invalid_boundary_input(connection, body):
    with pytest.raises(ValueError):
        DashboardBackend(connection).update_knowledge(
            "dummy.pst.services", body, actor_id=1
        )


def test_migration_defines_constraints_and_exact_dummy_guestbook_url():
    migration = open(
        "migrations/versions/0007_knowledge_base.py", encoding="utf-8"
    ).read()

    assert "knowledge_base" in migration
    assert "DUMMY" in migration and "VERIFIED" in migration
    assert "length(content) <= 20000" in migration
    assert "https://s.bps.go.id/tamu1306" in migration
    assert "BELUM DIVERIFIKASI" in migration
