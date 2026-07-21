from fastapi.testclient import TestClient

from operational.webhook import create_webhook_app


SECRET = "s" * 32


class Store:
    def __init__(self):
        self.inbound = []
        self.receipts = []

    def admit_inbound(self, event_id, phone, body):
        self.inbound.append((event_id, phone, body))
        return "pending"

    def record_receipt(self, provider_message_id, status):
        self.receipts.append((provider_message_id, status))
        return status


def client(store=None, **kwargs):
    return TestClient(
        create_webhook_app(
            store or Store(),
            webhook_secret=SECRET,
            instance="marawa",
            production=True,
            **kwargs,
        )
    )


def payload(event="messages.upsert"):
    if event == "messages.update":
        return {
            "event": event,
            "instance": "marawa",
            "data": {"key": {"id": "provider-1"}, "update": {"status": 3}},
        }
    return {
        "event": event,
        "instance": "marawa",
        "data": {
            "key": {
                "id": "wamid-1",
                "remoteJid": "628123456789@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {"conversation": "Halo"},
        },
    }


def test_rejects_missing_or_wrong_secret_without_side_effect():
    store = Store()
    app = client(store)

    assert app.post("/webhook", json=payload()).status_code == 401
    assert (
        app.post(
            "/webhook", json=payload(), headers={"X-Webhook-Secret": "x" * 32}
        ).status_code
        == 401
    )
    assert store.inbound == []


def test_rejects_oversize_malformed_non_object_and_wrong_instance():
    store = Store()
    app = client(store, max_body_bytes=100)
    headers = {"X-Webhook-Secret": SECRET}

    assert app.post("/webhook", content=b"x" * 101, headers=headers).status_code == 413
    assert app.post("/webhook", content=b"{", headers=headers).status_code == 400
    assert app.post("/webhook", json=[], headers=headers).status_code == 422
    wrong = payload()
    wrong["instance"] = "other"
    assert (
        client(store).post("/webhook", json=wrong, headers=headers).status_code == 403
    )
    assert store.inbound == []


def test_admits_valid_inbound_before_success_response():
    store = Store()
    response = client(store).post(
        "/webhook", json=payload(), headers={"X-Webhook-Secret": SECRET}
    )

    assert response.status_code == 202
    assert response.json() == {"status": "pending"}
    assert store.inbound == [("wamid-1", "628123456789", "Halo")]


def test_records_delivery_receipt_idempotently():
    store = Store()
    response = client(store).post(
        "/webhook",
        json=payload("messages.update"),
        headers={"X-Webhook-Secret": SECRET},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "DELIVERY_ACK"}
    assert store.receipts == [("provider-1", "DELIVERY_ACK")]


def test_ignored_valid_provider_event_is_acknowledged_without_persistence():
    store = Store()
    ignored = payload()
    ignored["data"]["key"]["fromMe"] = True

    response = client(store).post(
        "/webhook", json=ignored, headers={"X-Webhook-Secret": SECRET}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert store.inbound == []


def test_short_secret_refuses_app_construction():
    try:
        create_webhook_app(Store(), webhook_secret="short", instance="marawa")
    except ValueError as exc:
        assert str(exc) == "WEBHOOK_SECRET must be at least 32 characters"
    else:
        raise AssertionError("short secret accepted")
