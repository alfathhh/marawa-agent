import os

import pytest
from sqlalchemy import create_engine, text

from operational.dashboard_backend import DashboardBackend
from operational.dashboard_security import verify_password

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


def create(backend, username, role="petugas"):
    return backend.create_user(
        {"username": username, "password": "temporary-pass", "role": role}
    )


def test_create_user_is_temporary_and_session_exposes_lifecycle(backend):
    user = create(backend, "new.operator")

    session = backend.session_user(user["id"])

    assert session == {
        "id": user["id"],
        "role": "petugas",
        "active": True,
        "session_version": 1,
        "must_change_password": True,
    }


def test_user_mutations_reject_unknown_body_fields(backend):
    user = create(backend, "closed.fields")

    with pytest.raises(ValueError):
        backend.create_user(
            {
                "username": "another.user",
                "password": "temporary-pass",
                "role": "petugas",
                "active": False,
            }
        )
    with pytest.raises(ValueError):
        backend.change_password(
            user["id"],
            {"current_password": "temporary-pass", "password": "new-password1", "x": 1},
        )
    with pytest.raises(ValueError):
        backend.reset_password(user["id"], {"password": "new-password1", "x": 1})
    with pytest.raises(ValueError):
        backend.set_user_active(user["id"], {"active": False, "x": 1}, actor_id=999)


def test_change_password_requires_current_password_and_clears_temporary_flag(
    backend, connection
):
    user = create(backend, "change.password")

    with pytest.raises(ValueError):
        backend.change_password(
            user["id"],
            {"current_password": "wrong-password", "password": "new-password1"},
            actor_id=user["id"],
        )
    changed = backend.change_password(
        user["id"],
        {"current_password": "temporary-pass", "password": "new-password1"},
        actor_id=user["id"],
    )

    authenticated = backend.authenticate("change.password")
    assert changed["must_change_password"] is False
    assert changed["session_version"] == 2
    assert verify_password("new-password1", authenticated["password_hash"])
    assert (
        connection.execute(
            text("SELECT count(*) FROM audit_log WHERE action='user.password.change'")
        ).scalar_one()
        == 1
    )


def test_superadmin_reset_bumps_version_and_forces_change(backend, connection):
    admin = create(backend, "reset.admin", "superadmin")
    target = create(backend, "reset.target")

    reset = backend.reset_password(
        target["id"], {"password": "reset-password1"}, actor_id=admin["id"]
    )

    assert reset["session_version"] == 2
    assert reset["must_change_password"] is True
    assert verify_password(
        "reset-password1", backend.authenticate("reset.target")["password_hash"]
    )
    assert (
        connection.execute(
            text("SELECT actor_id FROM audit_log WHERE action='user.password.reset'")
        ).scalar_one()
        == admin["id"]
    )


def test_activation_changes_bump_version_and_reject_self_disable(backend):
    admin = create(backend, "active.admin", "superadmin")
    target = create(backend, "active.target")

    disabled = backend.set_user_active(
        target["id"], {"active": False}, actor_id=admin["id"]
    )
    enabled = backend.set_user_active(
        target["id"], {"active": True}, actor_id=admin["id"]
    )

    assert (disabled["active"], disabled["session_version"]) == (False, 2)
    assert (enabled["active"], enabled["session_version"]) == (True, 3)
    with pytest.raises(ValueError):
        backend.set_user_active(admin["id"], {"active": False}, actor_id=admin["id"])


def test_cannot_disable_last_active_superadmin(backend):
    admin = create(backend, "last.admin", "superadmin")
    other = create(backend, "ordinary.user")

    with pytest.raises(ValueError):
        backend.set_user_active(admin["id"], {"active": False}, actor_id=other["id"])


def test_failed_change_rolls_back_mutation_and_audit_together(
    backend, connection, monkeypatch
):
    connection.execute(
        text("DELETE FROM dashboard_users WHERE username='atomic.change'")
    )
    connection.commit()
    user = create(backend, "atomic.change")
    savepoint = connection.begin_nested()
    original = backend._audit

    def fail_after_audit(*args):
        original(*args)
        raise RuntimeError("audit failure")

    monkeypatch.setattr(backend, "_audit", fail_after_audit)
    with pytest.raises(RuntimeError):
        backend.change_password(
            user["id"],
            {"current_password": "temporary-pass", "password": "new-password1"},
            actor_id=user["id"],
        )
    savepoint.rollback()

    assert (
        connection.execute(
            text("SELECT session_version FROM dashboard_users WHERE id=:id"),
            {"id": user["id"]},
        ).scalar_one()
        == 1
    )
    assert (
        connection.execute(
            text("SELECT count(*) FROM audit_log WHERE action='user.password.change'")
        ).scalar_one()
        == 0
    )
    connection.execute(
        text("DELETE FROM audit_log WHERE target=:target"),
        {"target": str(user["id"])},
    )
    connection.execute(
        text("DELETE FROM dashboard_users WHERE id=:id"), {"id": user["id"]}
    )
    connection.commit()


def test_migration_adds_auth_lifecycle_columns():
    migration = open(
        "migrations/versions/0006_auth_lifecycle.py", encoding="utf-8"
    ).read()

    assert "session_version" in migration
    assert "must_change_password" in migration
    assert 'down_revision = "0005"' in migration
