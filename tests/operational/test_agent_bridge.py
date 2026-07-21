import asyncio

from operational.bridge import process_inbound


class Store:
    def __init__(self):
        self.outbound = []
        self.done = []
        self.failed = []

    def enqueue_outbound(self, phone, body, dedupe_key):
        self.outbound.append((phone, body, dedupe_key))
        return 1

    def mark_inbound_done(self, event_id, token):
        self.done.append((event_id, token))
        return True

    def mark_inbound_failed(self, event_id, token, code):
        self.failed.append((event_id, token, code))
        return "PENDING"


async def runtime(text, phone):
    return {
        "text": "Jumlah penduduk tersedia dari sumber resmi.",
        "sources": [{"title": "SIMDASI", "url": "https://webapi.bps.go.id"}],
    }


def test_bridge_renders_sources_and_enqueues_with_event_dedupe():
    store = Store()
    row = {
        "event_id": "wamid-1",
        "phone": "628123456789",
        "body": "Penduduk",
        "claim_token": "w1",
    }

    result = asyncio.run(process_inbound(store, runtime, row))

    assert result == "DONE"
    assert store.outbound == [
        (
            "628123456789",
            "Jumlah penduduk tersedia dari sumber resmi.\n\nSumber:\n• SIMDASI — https://webapi.bps.go.id",
            "inbound:wamid-1:1",
        )
    ]
    assert store.done == [("wamid-1", "w1")]


def test_bridge_rejects_unofficial_source_and_retries_without_outbound():
    async def bad_source(text, phone):
        return {
            "text": "data",
            "sources": [{"title": "Blog", "url": "https://evil.example"}],
        }

    store = Store()
    row = {
        "event_id": "wamid-2",
        "phone": "628123456789",
        "body": "x",
        "claim_token": "w2",
    }

    assert asyncio.run(process_inbound(store, bad_source, row)) == "PENDING"
    assert store.outbound == []
    assert store.failed == [("wamid-2", "w2", "invalid_agent_output")]


def test_runtime_exception_is_safe_and_does_not_lose_inbound():
    async def broken(text, phone):
        raise RuntimeError("secret provider trace")

    store = Store()
    row = {
        "event_id": "wamid-3",
        "phone": "628123456789",
        "body": "x",
        "claim_token": "w3",
    }

    assert asyncio.run(process_inbound(store, broken, row)) == "PENDING"
    assert store.failed == [("wamid-3", "w3", "agent_unavailable")]
    assert "secret" not in str(store.failed)


def test_empty_or_oversize_output_is_not_sent():
    async def invalid(text, phone):
        return {"text": "x" * 12001, "sources": []}

    store = Store()
    row = {
        "event_id": "wamid-4",
        "phone": "628123456789",
        "body": "x",
        "claim_token": "w4",
    }

    assert asyncio.run(process_inbound(store, invalid, row)) == "PENDING"
    assert store.outbound == []
