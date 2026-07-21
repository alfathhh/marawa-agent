import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from operational.handover import GUESTBOOK_URL, HandoverStore

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
            if transaction.is_active:
                transaction.rollback()
    except Exception as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")
    finally:
        engine.dispose()


def test_request_is_idempotent_per_user(connection):
    store = HandoverStore(connection)

    first = store.request(
        "628111111111",
        deadline_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    duplicate = store.request(
        "628111111111",
        deadline_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    assert first == duplicate
    row = connection.execute(
        text("SELECT state, status FROM handovers WHERE id=:id"), {"id": first}
    ).one()
    assert row == ("HANDOVER_PENDING", "PENDING")


def test_claim_is_atomic_first_wins_and_returns_exact_owner(connection):
    store = HandoverStore(connection)
    handover_id = store.request("628222222222")

    winner = store.claim(handover_id, "admin-a")
    loser = store.claim(handover_id, "admin-b")

    assert winner == {"id": handover_id, "owner_id": "admin-a", "generation": 1}
    assert loser is None


def test_owner_actions_require_current_generation_fence(connection):
    store = HandoverStore(connection)
    handover_id = store.request("628333333333")
    claim = store.claim(handover_id, "admin-a")

    assert store.release(handover_id, "admin-a", claim["generation"] + 1) is False
    assert store.release(handover_id, "admin-b", claim["generation"]) is False
    assert store.release(handover_id, "admin-a", claim["generation"]) is True
    assert store.claim(handover_id, "admin-b") == {
        "id": handover_id,
        "owner_id": "admin-b",
        "generation": 3,
    }


def test_resolve_closes_handover_and_restores_bot(connection):
    store = HandoverStore(connection)
    handover_id = store.request("628444444444")
    claim = store.claim(handover_id, "admin-a")

    assert store.resolve(handover_id, "admin-a", claim["generation"]) is True
    row = connection.execute(
        text("SELECT state, status FROM handovers WHERE id=:id"), {"id": handover_id}
    ).one()
    assert row == ("BOT_ACTIVE", "RESOLVED")
    assert store.resolve(handover_id, "admin-a", claim["generation"]) is False


def test_deadline_processing_is_idempotent_and_uses_exact_guestbook_fallback(
    connection,
):
    store = HandoverStore(connection)
    handover_id = store.request(
        "628555555555",
        deadline_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    first = store.process_deadlines()
    second = store.process_deadlines()

    assert first == [{"id": handover_id, "guestbook_url": GUESTBOOK_URL}]
    assert second == []
    row = connection.execute(
        text("SELECT state, status, fallback_url FROM handovers WHERE id=:id"),
        {"id": handover_id},
    ).one()
    assert row == ("BOT_ACTIVE", "EXPIRED", "https://s.bps.go.id/tamu1306")


def test_failed_handover_uses_exact_guestbook_fallback(connection):
    store = HandoverStore(connection)
    handover_id = store.request("628666666666")

    assert store.fail(handover_id) == {
        "id": handover_id,
        "guestbook_url": GUESTBOOK_URL,
    }
    assert store.fail(handover_id) is None
    row = connection.execute(
        text("SELECT status, fallback_url FROM handovers WHERE id=:id"),
        {"id": handover_id},
    ).one()
    assert row == ("FAILED", GUESTBOOK_URL)


def test_database_rejects_invalid_state_and_status(connection):
    with pytest.raises(Exception):
        connection.execute(
            text("""
            INSERT INTO handovers (user_phone, state, status)
            VALUES ('628777777777', 'INVALID', 'INVALID')
        """)
        )
    connection.rollback()


def test_migration_contract_declares_partial_open_uniqueness():
    migration = open("migrations/versions/0004_handover.py", encoding="utf-8").read()

    assert "uq_handovers_open_user" in migration
    assert "status IN ('PENDING','ACTIVE')" in migration
    assert (
        "BOT_ACTIVE" in migration
        and "HANDOVER_PENDING" in migration
        and "ADMIN_ACTIVE" in migration
    )
    assert all(status in migration for status in ("RESOLVED", "FAILED", "EXPIRED"))
    assert GUESTBOOK_URL in migration


def test_guestbook_fallback_is_not_configurable():
    assert GUESTBOOK_URL == "https://s.bps.go.id/tamu1306"
    assert HandoverStore.__init__.__code__.co_argcount == 2
