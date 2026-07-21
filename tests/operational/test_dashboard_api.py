from fastapi.testclient import TestClient

from operational.dashboard import create_dashboard_app
from operational.dashboard_security import hash_password


SECRET = "d" * 32


class Backend:
    def __init__(self):
        self.users = {
            "admin": {
                "id": 1,
                "username": "admin",
                "role": "superadmin",
                "password_hash": hash_password("password-admin"),
                "active": True,
            }
        }
        self.actions = []

    def authenticate(self, username):
        return self.users.get(username)

    def list_handover(self):
        return [{"code": "ABCD", "phone": "628123456789", "status": "PENDING"}]

    def handover_action(self, action, code, uid, body):
        self.actions.append((action, code, uid, body))
        return {"status": "ok"}

    def list_users(self):
        return [
            {k: v for k, v in user.items() if k != "password_hash"}
            for user in self.users.values()
        ]

    def create_user(self, body):
        self.actions.append(("create_user", body))
        return {"id": 2}

    def get_settings(self):
        return {"BOT_ENABLED": True, "ADMIN_CLAIM_TIMEOUT_MIN": 5}

    def set_settings(self, body):
        self.actions.append(("settings", body))
        return body


class Evolution:
    async def connection_status(self):
        return {"instance": "marawa", "state": "connected"}

    async def pairing_qr(self):
        return {"instance": "marawa", "state": "connected", "qr": None}

    async def logout(self):
        return {"instance": "marawa", "state": "disconnected"}


def login(client):
    response = client.post(
        "/dashboard/api/auth/login",
        json={"username": "admin", "password": "password-admin"},
    )
    assert response.status_code == 200
    return response.json()["csrf"]


def test_login_cookie_me_and_logout():
    client = TestClient(
        create_dashboard_app(Backend(), Evolution(), session_secret=SECRET)
    )
    csrf = login(client)
    assert client.get("/dashboard/api/auth/me").json()["role"] == "superadmin"
    assert (
        client.post("/dashboard/api/auth/logout", headers={"X-CSRF": csrf}).status_code
        == 204
    )
    assert client.get("/dashboard/api/auth/me").status_code == 401


def test_mutation_requires_csrf_and_superadmin():
    backend = Backend()
    client = TestClient(
        create_dashboard_app(backend, Evolution(), session_secret=SECRET)
    )
    csrf = login(client)
    assert (
        client.put("/dashboard/api/settings", json={"BOT_ENABLED": False}).status_code
        == 403
    )
    assert (
        client.put(
            "/dashboard/api/settings",
            json={"BOT_ENABLED": False},
            headers={"X-CSRF": csrf},
        ).status_code
        == 200
    )
    assert backend.actions == [("settings", {"BOT_ENABLED": False})]


def test_queue_masks_phone_for_petugas_and_claims_with_owner():
    backend = Backend()
    backend.users["staff"] = {
        "id": 2,
        "username": "staff",
        "role": "petugas",
        "password_hash": hash_password("password-staff"),
        "active": True,
    }
    client = TestClient(
        create_dashboard_app(backend, Evolution(), session_secret=SECRET)
    )
    csrf = client.post(
        "/dashboard/api/auth/login",
        json={"username": "staff", "password": "password-staff"},
    ).json()["csrf"]
    assert client.get("/dashboard/api/handover").json()[0]["phone"] == "********6789"
    assert (
        client.post(
            "/dashboard/api/handover/ABCD/claim", json={}, headers={"X-CSRF": csrf}
        ).status_code
        == 200
    )
    assert backend.actions[0][:3] == ("claim", "ABCD", 2)
    assert client.get("/dashboard/api/users").status_code == 403


def test_superadmin_users_settings_and_evolution_ops():
    client = TestClient(
        create_dashboard_app(Backend(), Evolution(), session_secret=SECRET)
    )
    csrf = login(client)
    assert client.get("/dashboard/api/users").status_code == 200
    assert (
        client.post(
            "/dashboard/api/users",
            json={"username": "baru", "role": "petugas", "password": "password-baru"},
            headers={"X-CSRF": csrf},
        ).status_code
        == 201
    )
    assert client.get("/dashboard/api/settings").status_code == 200
    assert (
        client.get("/dashboard/api/ops/evolution/status").json()["state"] == "connected"
    )
    assert (
        client.post(
            "/dashboard/api/ops/evolution/qr", headers={"X-CSRF": csrf}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/dashboard/api/ops/evolution/logout", headers={"X-CSRF": csrf}
        ).json()["state"]
        == "disconnected"
    )


def test_bad_login_and_inactive_user_are_generic():
    backend = Backend()
    backend.users["admin"]["active"] = False
    client = TestClient(
        create_dashboard_app(backend, Evolution(), session_secret=SECRET)
    )
    response = client.post(
        "/dashboard/api/auth/login",
        json={"username": "admin", "password": "password-admin"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Kredensial tidak valid"}
