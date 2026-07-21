import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from operational.dashboard import create_dashboard_app
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


class Evolution:
    pass


def _login(client, username, password):
    response = client.post(
        "/dashboard/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200


def test_overview_summarizes_durable_operational_state(connection):
    backend = DashboardBackend(connection)
    backend.create_user(
        {
            "username": "overview.admin",
            "password": "password-admin",
            "role": "superadmin",
        }
    )
    inactive = backend.create_user(
        {"username": "inactive.user", "password": "password-user", "role": "petugas"}
    )
    backend.set_user_active(inactive["id"], {"active": False})
    connection.execute(
        text(
            "INSERT INTO inbound_events (event_id, phone, body, status) VALUES ('ov-1','6281','x','DONE')"
        )
    )
    connection.execute(
        text(
            "INSERT INTO outbound_messages (phone, body, status) VALUES ('6281','x','ACCEPTED')"
        )
    )
    connection.execute(
        text("INSERT INTO handovers (user_phone, status) VALUES ('6282','PENDING')")
    )

    result = backend.operational_overview()

    assert result["inbound"] == {"PENDING": 0, "PROCESSING": 0, "DONE": 1, "DEAD": 0}
    assert result["outbound"]["ACCEPTED"] == 1
    assert result["handovers"] == {
        "PENDING": 1,
        "ACTIVE": 0,
        "RESOLVED": 0,
        "FAILED": 0,
        "EXPIRED": 0,
    }
    assert result["knowledge"] == {"DUMMY": 3, "VERIFIED": 0}
    assert result["active_users"] == 1


def test_latest_audit_is_capped_and_contains_only_safe_fields(connection):
    backend = DashboardBackend(connection)
    actor = backend.create_user(
        {"username": "audit.admin", "password": "password-admin", "role": "superadmin"}
    )
    for index in range(55):
        backend.audit(actor["id"], "test.action", str(index))

    rows = backend.latest_audit()

    assert len(rows) == 50
    assert rows[0]["target"] == "54"
    assert set(rows[0]) == {
        "id",
        "actor_id",
        "actor_username",
        "action",
        "target",
        "created_at",
    }
    assert rows[0]["actor_username"] == "audit.admin"
    assert not any("password" in key or "payload" in key for row in rows for key in row)


def test_overview_and_audit_endpoints_require_superadmin(connection):
    backend = DashboardBackend(connection)
    backend.create_user(
        {"username": "api.admin", "password": "password-admin", "role": "superadmin"}
    )
    backend.create_user(
        {"username": "api.staff", "password": "password-staff", "role": "petugas"}
    )
    connection.execute(text("UPDATE dashboard_users SET must_change_password=false"))
    client = TestClient(
        create_dashboard_app(backend, Evolution(), session_secret="s" * 32)
    )

    assert client.get("/dashboard/api/overview").status_code == 401
    _login(client, "api.staff", "password-staff")
    assert client.get("/dashboard/api/overview").status_code == 403
    assert client.get("/dashboard/api/audit").status_code == 403
    _login(client, "api.admin", "password-admin")
    overview = client.get("/dashboard/api/overview")
    audit = client.get("/dashboard/api/audit")

    assert overview.status_code == 200
    assert set(overview.json()) == {
        "inbound",
        "outbound",
        "handovers",
        "knowledge",
        "active_users",
    }
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "dashboard.login.success"
