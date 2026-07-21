import httpx
from fastapi.testclient import TestClient

from operational.dashboard import create_dashboard_app
from operational.dashboard_security import hash_password


SECRET = "h" * 32


class Backend:
    def __init__(self):
        self.user = {
            "id": 7,
            "role": "superadmin",
            "active": True,
            "password_hash": hash_password("correct-password"),
        }
        self.audits = []
        self.calls = []

    def authenticate(self, username):
        return self.user if username == "admin" else None

    def session_user(self, uid):
        return self.user if uid == 7 else None

    def audit(self, actor_id, action, target):
        self.audits.append((actor_id, action, target))

    def handover_action(self, action, code, uid, body):
        self.calls.append((action, body))
        return {"ok": True}

    def create_user(self, body):
        self.calls.append(("create_user", body))
        return {"id": 8}

    def set_settings(self, body):
        self.calls.append(("settings", body))
        return body


class Evolution:
    async def pairing_qr(self):
        return {"qr": None}

    async def logout(self):
        return {"state": "disconnected"}


def app_client(backend=None, evolution=None):
    backend = backend or Backend()
    return TestClient(
        create_dashboard_app(backend, evolution or Evolution(), session_secret=SECRET),
        raise_server_exceptions=False,
    ), backend


def login(client, body=None):
    response = client.post(
        "/dashboard/api/auth/login",
        json=body or {"username": "admin", "password": "correct-password"},
    )
    return response, response.json().get("csrf")


def test_json_body_limit_accepts_boundary_and_rejects_one_byte_over():
    client, _ = app_client()
    _, csrf = login(client)
    headers = {"X-CSRF": csrf, "content-type": "application/json"}
    prefix = b'{"message":"'
    suffix = b'","generation":1}'
    at_limit = prefix + (b"x" * (65536 - len(prefix) - len(suffix))) + suffix

    accepted = client.post(
        "/dashboard/api/handover/1/send", content=at_limit, headers=headers
    )
    rejected = client.post(
        "/dashboard/api/handover/1/send", content=at_limit + b" ", headers=headers
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 413
    assert rejected.json() == {"detail": "Permintaan terlalu besar"}


def test_malformed_json_and_non_object_are_generic_without_backend_call():
    client, backend = app_client()
    _, csrf = login(client)
    headers = {"X-CSRF": csrf, "content-type": "application/json"}

    malformed = client.post(
        "/dashboard/api/handover/1/claim", content=b"{", headers=headers
    )
    array = client.post(
        "/dashboard/api/handover/1/claim", content=b"[]", headers=headers
    )

    assert malformed.status_code == 400
    assert malformed.json() == {"detail": "Permintaan tidak valid"}
    assert array.status_code == 422
    assert array.json() == {"detail": "Permintaan tidak valid"}
    assert backend.calls == []


def test_api_schemas_reject_missing_unknown_and_wrong_typed_fields():
    client, backend = app_client()
    _, csrf = login(client)
    headers = {"X-CSRF": csrf}

    responses = [
        client.post("/dashboard/api/auth/login", json={"username": "admin"}),
        client.post(
            "/dashboard/api/users",
            json={
                "username": "new",
                "password": "long-enough-password",
                "role": "petugas",
                "admin": True,
            },
            headers=headers,
        ),
        client.put(
            "/dashboard/api/settings", json={"BOT_ENABLED": "yes"}, headers=headers
        ),
        client.post(
            "/dashboard/api/handover/1/release",
            json={"generation": True},
            headers=headers,
        ),
        client.post(
            "/dashboard/api/handover/1/claim",
            json={"generation": 1},
            headers=headers,
        ),
    ]

    assert [response.status_code for response in responses] == [422] * 5
    assert all(
        response.json() == {"detail": "Permintaan tidak valid"}
        for response in responses
    )
    assert backend.calls == []


def test_audits_login_failure_success_logout_and_evolution_mutations():
    client, backend = app_client()

    failed, _ = login(client, {"username": "admin", "password": "wrong-password"})
    succeeded, csrf = login(client)
    qr = client.post("/dashboard/api/ops/evolution/qr", headers={"X-CSRF": csrf})
    evo_logout = client.post(
        "/dashboard/api/ops/evolution/logout", headers={"X-CSRF": csrf}
    )
    logout = client.post("/dashboard/api/auth/logout", headers={"X-CSRF": csrf})

    assert [
        failed.status_code,
        succeeded.status_code,
        qr.status_code,
        evo_logout.status_code,
        logout.status_code,
    ] == [401, 200, 200, 200, 204]
    assert backend.audits == [
        (None, "dashboard.login.failure", "admin"),
        (7, "dashboard.login.success", "7"),
        (7, "dashboard.evolution.qr", "evolution"),
        (7, "dashboard.evolution.logout", "evolution"),
        (7, "dashboard.logout", "7"),
    ]


def test_audit_hook_is_optional():
    backend = Backend()
    backend.audit = None
    client, _ = app_client(backend)

    response, _ = login(client)

    assert response.status_code == 200


def test_evolution_http_errors_and_error_payloads_are_sanitized_to_502():
    class BrokenEvolution(Evolution):
        async def pairing_qr(self):
            request = httpx.Request("GET", "https://evolution/private")
            response = httpx.Response(500, request=request, text="secret upstream body")
            raise httpx.HTTPStatusError(
                "secret upstream body", request=request, response=response
            )

        async def logout(self):
            return {"error": {"code": "evolution_unavailable", "raw": "secret"}}

    client, _ = app_client(evolution=BrokenEvolution())
    _, csrf = login(client)

    qr = client.post("/dashboard/api/ops/evolution/qr", headers={"X-CSRF": csrf})
    logout = client.post(
        "/dashboard/api/ops/evolution/logout", headers={"X-CSRF": csrf}
    )

    assert qr.status_code == logout.status_code == 502
    assert qr.json() == logout.json() == {"detail": "Layanan Evolution tidak tersedia"}
    assert "secret" not in qr.text + logout.text


def test_unexpected_api_errors_are_generic():
    backend = Backend()

    def explode(_username):
        raise RuntimeError("database password leaked")

    backend.authenticate = explode
    client, _ = app_client(backend)

    response = client.post(
        "/dashboard/api/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Kesalahan internal"}
    assert "password leaked" not in response.text
