import os

import pytest
from sqlalchemy import create_engine, text

from operational.dashboard_backend import DashboardBackend
from operational.dashboard_security import verify_password
from operational.handover import HandoverStore

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


@pytest.fixture
def backend(connection):
    return DashboardBackend(connection)


def test_user_creation_authentication_and_listing_hide_hash(backend, connection):
    created = backend.create_user(
        {"username": "admin.satu", "password": "rahasia-aman", "role": "superadmin"},
        actor_id=None,
    )

    authenticated = backend.authenticate("admin.satu")
    listed = backend.list_users()

    assert created == {
        "id": created["id"],
        "username": "admin.satu",
        "role": "superadmin",
        "active": True,
    }
    assert authenticated["id"] == created["id"]
    assert verify_password("rahasia-aman", authenticated["password_hash"])
    assert listed == [created]
    assert "password_hash" not in listed[0]
    assert (
        connection.execute(
            text("SELECT count(*) FROM audit_log WHERE action='user.create'")
        ).scalar_one()
        == 1
    )


@pytest.mark.parametrize(
    "body",
    [
        {"username": "x", "password": "rahasia-aman", "role": "petugas"},
        {"username": "valid.user", "password": "short", "role": "petugas"},
        {"username": "valid.user", "password": "rahasia-aman", "role": "owner"},
    ],
)
def test_create_user_rejects_invalid_fields(backend, body):
    with pytest.raises(ValueError):
        backend.create_user(body, actor_id=None)


def test_settings_are_allowlisted_validated_and_audited(backend, connection):
    actor = backend.create_user(
        {"username": "settings.admin", "password": "rahasia-aman", "role": "superadmin"}
    )
    result = backend.set_settings({"ADMIN_CLAIM_TIMEOUT_MIN": 15}, actor_id=actor["id"])

    assert result == {"ADMIN_CLAIM_TIMEOUT_MIN": 15}
    assert backend.get_settings() == result
    assert (
        connection.execute(
            text("SELECT actor_id FROM audit_log WHERE action='settings.set'")
        ).scalar_one()
        == actor["id"]
    )
    with pytest.raises(ValueError):
        backend.set_settings({"unknown": True}, actor_id=actor["id"])
    with pytest.raises(ValueError):
        backend.set_settings({"ADMIN_CLAIM_TIMEOUT_MIN": 1441}, actor_id=actor["id"])


def test_handover_actions_are_fenced_audited_and_send_enqueues(backend, connection):
    actor = backend.create_user(
        {"username": "handover.admin", "password": "rahasia-aman", "role": "petugas"}
    )
    handover_id = HandoverStore(connection).request("628123456789")

    claim = backend.handover_action("claim", str(handover_id), actor["id"], {})
    sent = backend.handover_action(
        "send",
        str(handover_id),
        actor["id"],
        {"generation": claim["generation"], "message": "Halo"},
    )

    assert sent["status"] == "QUEUED"
    assert connection.execute(
        text("SELECT phone, body FROM outbound_messages WHERE id=:id"),
        {"id": sent["id"]},
    ).one() == ("628123456789", "Halo")
    assert (
        connection.execute(
            text("SELECT count(*) FROM audit_log WHERE actor_id=:id"),
            {"id": actor["id"]},
        ).scalar_one()
        == 2
    )
    with pytest.raises(ValueError):
        backend.handover_action(
            "send",
            str(handover_id),
            12,
            {"generation": claim["generation"], "message": "no"},
        )


def test_list_and_release_handover(backend, connection):
    actor = backend.create_user(
        {"username": "release.admin", "password": "rahasia-aman", "role": "petugas"}
    )
    handover_id = HandoverStore(connection).request("628000000001")
    claim = backend.handover_action("claim", str(handover_id), actor["id"], {})

    rows = backend.list_handover()
    released = backend.handover_action(
        "release", str(handover_id), actor["id"], {"generation": claim["generation"]}
    )

    assert rows[0]["phone"] == "628000000001"
    assert rows[0]["status"] == "ACTIVE"
    assert released["ok"] is True


def test_migration_contract_has_dashboard_tables_and_constraints():
    migration = open("migrations/versions/0005_dashboard.py", encoding="utf-8").read()

    assert all(
        name in migration
        for name in ("dashboard_users", "settings", "audit_log", "JSONB")
    )
    assert "petugas" in migration and "superadmin" in migration
