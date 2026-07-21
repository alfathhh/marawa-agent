import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from prototype_v1.app import app, store
from prototype_v1.models import Message
from prototype_v1.state import MAX_MESSAGES, SessionStore


@pytest.fixture(autouse=True)
def clean_store():
    store.sessions.clear()
    store._locks.clear()
    yield
    store.sessions.clear()
    store._locks.clear()


def test_store_session_contract_and_idle_expiry():
    now = [datetime.now(UTC).timestamp()]
    sstore = SessionStore("boot_test", clock=lambda: now[0])
    session = sstore.create()
    assert session.session_id.startswith("pv1_") and len(session.session_id) > 20
    assert session.server_generation == "boot_test"
    assert session.state_version == 0 and session.lock is not None
    now[0] += 7201
    with pytest.raises(TimeoutError, match="session_expired"):
        sstore.get(session.session_id)


def test_store_capacity_is_100_and_expired_are_purged():
    sstore = SessionStore("boot_test")
    sessions = [sstore.create() for _ in range(100)]
    with pytest.raises(RuntimeError, match="session_capacity"):
        sstore.create()
    sessions[0].last_active_at = datetime.now(UTC) - timedelta(hours=3)
    assert sstore.create().session_id.startswith("pv1_")


def test_store_messages_are_capped_and_duplicate_response_is_exact_once():
    sstore = SessionStore("boot_test")
    session = sstore.create()
    for i in range(MAX_MESSAGES + 3):
        sstore.append_message(session, Message("user", "x", str(i), datetime.now(UTC)))
    assert len(session.messages) == MAX_MESSAGES
    response = {"data": {"state_version": 1}}
    assert sstore.commit(session, "m", response) is response
    assert sstore.commit(session, "m", {"different": True}) is response
    assert session.state_version == 1


@pytest.mark.anyio
async def test_message_endpoint_validates_uuid_length_and_schema():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/prototype/sessions", headers={"Origin": "http://127.0.0.1:8010"}, json={})
        data = created.json()["data"]
        headers = {"Origin": "http://127.0.0.1:8010", "X-Server-Generation": data["server_generation"]}
        bad = await client.post(f"/api/prototype/sessions/{data['session_id']}/messages", headers=headers, json={"message_id": "x", "state_version": 0, "text": "hi"})
        assert bad.status_code == 422
        too_long = await client.post(f"/api/prototype/sessions/{data['session_id']}/messages", headers=headers, json={"message_id": str(uuid.uuid4()), "state_version": 0, "text": "x" * 8001})
        assert too_long.status_code == 422


@pytest.mark.anyio
async def test_message_idempotency_and_version_conflict():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/prototype/sessions", headers={"Origin": "http://127.0.0.1:8010"}, json={})
        data = created.json()["data"]
        headers = {"Origin": "http://127.0.0.1:8010", "X-Server-Generation": data["server_generation"]}
        body = {"message_id": str(uuid.uuid4()), "state_version": 0, "text": "halo"}
        first = await client.post(f"/api/prototype/sessions/{data['session_id']}/messages", headers=headers, json=body)
        duplicate = await client.post(f"/api/prototype/sessions/{data['session_id']}/messages", headers=headers, json=body)
        assert first.json() == duplicate.json()
        assert first.json()["data"]["state_version"] == 1
        conflict = await client.post(f"/api/prototype/sessions/{data['session_id']}/messages", headers=headers, json={"message_id": str(uuid.uuid4()), "state_version": 0, "text": "lagi"})
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "state_version_conflict"


@pytest.mark.anyio
async def test_get_and_delete_are_exact_and_idempotent():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.get("/api/prototype/sessions/pv1_missing", headers={"X-Server-Generation": "no"})
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "session_not_found"
        deleted = await client.delete(
            "/api/prototype/sessions/pv1_missing",
            headers={"Origin": "http://127.0.0.1:8010"},
        )
        assert deleted.status_code == 204 and deleted.content == b""


def test_frontend_contract_tokens():
    js = open("prototype_v1/static/app.js").read()
    css = open("prototype_v1/static/styles.css").read()
    html = open("prototype_v1/static/index.html").read()
    for token in ("schema_version", "delivery_state", "pending", "failed", "server_generation", "localStorage", "confirm"):
        assert token in js
    assert "transcript.slice(-100)" in js
    assert "100dvh" in css and "focus-visible" in css and "44px" in css
    assert 'aria-live' in html


def test_server_message_limit_is_40():
    assert MAX_MESSAGES == 40
