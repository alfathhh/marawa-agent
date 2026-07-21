import asyncio

import httpx

from operational.evolution import (
    EvolutionClient,
    advance_delivery,
    parse_event,
)


def upsert(**key_changes):
    key = {
        "id": "wamid-1",
        "remoteJid": "628123456789@s.whatsapp.net",
        "fromMe": False,
        **key_changes,
    }
    return {
        "event": "messages.upsert",
        "data": {
            "key": key,
            "pushName": "Rina",
            "message": {"conversation": "Cari data penduduk"},
        },
    }


def test_parses_direct_inbound_text_to_closed_shape():
    assert parse_event(upsert()) == {
        "kind": "inbound",
        "event_id": "wamid-1",
        "phone": "628123456789",
        "name": "Rina",
        "text": "Cari data penduduk",
    }


def test_ignores_from_me_group_invalid_phone_and_unsupported_media():
    assert parse_event(upsert(fromMe=True)) is None
    assert parse_event(upsert(remoteJid="123@g.us")) is None
    assert parse_event(upsert(remoteJid="x@s.whatsapp.net")) is None
    payload = upsert()
    payload["data"]["message"] = {"audioMessage": {}}
    assert parse_event(payload) is None


def test_parses_delivery_receipts_from_known_evolution_shapes():
    assert parse_event({
        "event": "messages.update",
        "data": {"key": {"id": "provider-1"}, "update": {"status": 3}},
    }) == {"kind": "delivery", "provider_message_id": "provider-1", "status": "DELIVERY_ACK"}
    assert parse_event({
        "event": "messages.update",
        "data": {"keyId": "provider-2", "status": "ERROR"},
    }) == {"kind": "delivery", "provider_message_id": "provider-2", "status": "ERROR"}


def test_delivery_status_is_monotonic_but_new_error_evidence_is_preserved():
    assert advance_delivery("ACCEPTED", "SERVER_ACK") == "SERVER_ACK"
    assert advance_delivery("READ", "DELIVERY_ACK") == "READ"
    assert advance_delivery("DELIVERY_ACK", "ERROR") == "ERROR"
    assert advance_delivery("ERROR", "READ") == "ERROR"


def test_send_text_2xx_is_only_accepted_not_delivered():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["apikey"] = request.headers["apikey"]
        return httpx.Response(201, json={"key": {"id": "provider-1"}})

    async def run():
        async with httpx.AsyncClient(
            base_url="https://evolution.example",
            transport=httpx.MockTransport(handler),
        ) as http:
            return await EvolutionClient(http, "secret", "marawa").send_text(
                "628123456789", "Halo"
            )

    assert asyncio.run(run()) == {
        "status": "ACCEPTED",
        "provider_message_id": "provider-1",
    }
    assert seen == {
        "url": "https://evolution.example/message/sendText/marawa",
        "apikey": "secret",
    }


def test_send_text_hides_upstream_body_and_secret():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(500, text="secret raw provider body")
        )
        async with httpx.AsyncClient(
            base_url="https://evolution.example", transport=transport
        ) as http:
            return await EvolutionClient(http, "secret", "marawa").send_text(
                "628123456789", "Halo"
            )

    result = asyncio.run(run())

    assert result == {"error": {"code": "evolution_unavailable"}}
    assert "secret" not in str(result)


def test_rejects_unknown_or_malformed_event_without_exception():
    assert parse_event({"event": "connection.update", "data": {}}) is None
    assert parse_event({"event": "messages.update", "data": {}}) is None
    assert parse_event([]) is None


def test_connection_status_is_normalized():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"instance": {"state": "open"}})
        )
        async with httpx.AsyncClient(base_url="https://evolution.example", transport=transport) as http:
            return await EvolutionClient(http, "secret", "marawa").connection_status()

    assert asyncio.run(run()) == {"instance": "marawa", "state": "connected"}


def test_pairing_qr_accepts_only_valid_png_data_url():
    import base64
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nsmall").decode()

    async def run(payload):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(base_url="https://evolution.example", transport=transport) as http:
            return await EvolutionClient(http, "secret", "marawa").pairing_qr()

    assert asyncio.run(run({"base64": png})) == {
        "instance": "marawa", "state": "connecting",
        "qr": "data:image/png;base64," + png,
    }
    assert asyncio.run(run({"base64": base64.b64encode(b"not-png").decode()})) == {
        "instance": "marawa", "state": "connecting", "qr": None,
    }


def test_logout_uses_instance_endpoint_and_returns_disconnected():
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={})

    async def run():
        async with httpx.AsyncClient(base_url="https://evolution.example", transport=httpx.MockTransport(handler)) as http:
            return await EvolutionClient(http, "secret", "marawa").logout()

    assert asyncio.run(run()) == {"instance": "marawa", "state": "disconnected"}
    assert seen == {"method": "DELETE", "path": "/instance/logout/marawa"}
