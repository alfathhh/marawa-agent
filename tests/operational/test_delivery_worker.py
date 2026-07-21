import asyncio

from operational.delivery import deliver_batch


class Store:
    def __init__(self, rows):
        self.rows = rows
        self.accepted = []
        self.failed = []

    def claim_outbound(self, token, limit=10):
        return [{**row, "claim_token": token} for row in self.rows[:limit]]

    def mark_accepted(self, row_id, provider_id):
        self.accepted.append((row_id, provider_id))

    def mark_failed(self, row_id, token, error, max_attempts=8):
        self.failed.append((row_id, token, error, max_attempts))


class Evolution:
    def __init__(self, results):
        self.results = iter(results)

    async def send_text(self, phone, text):
        return next(self.results)


def test_worker_accepts_provider_response_and_keeps_claim_identity():
    store = Store([{"id": 1, "phone": "628123456789", "body": "Halo"}])
    result = asyncio.run(
        deliver_batch(
            store,
            Evolution([{"status": "ACCEPTED", "provider_message_id": "provider-1"}]),
            "worker-1",
        )
    )

    assert result == {"accepted": 1, "failed": 0}
    assert store.accepted == [(1, "provider-1")]
    assert store.failed == []


def test_worker_requeues_safe_provider_failure_without_leaking_detail():
    store = Store([{"id": 2, "phone": "628123456789", "body": "Halo"}])
    result = asyncio.run(
        deliver_batch(
            store,
            Evolution([{"error": {"code": "evolution_unavailable", "raw": "secret"}}]),
            "worker-2",
            max_attempts=3,
        )
    )

    assert result == {"accepted": 0, "failed": 1}
    assert store.failed == [(2, "worker-2", "evolution_unavailable", 3)]
    assert "secret" not in str(store.failed)


def test_empty_batch_is_noop():
    assert asyncio.run(deliver_batch(Store([]), Evolution([]), "worker")) == {
        "accepted": 0,
        "failed": 0,
    }
