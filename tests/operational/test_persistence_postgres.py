import os

import pytest
from sqlalchemy import create_engine, inspect, text

from operational.persistence import Store


DATABASE_URL = os.getenv(
    "MARAWA_TEST_DATABASE_URL",
    "postgresql+psycopg://marawa:marawa_test_only@127.0.0.1:55432/marawa_test",
)


@pytest.fixture
def connection():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        transaction = conn.begin()
        yield conn
        transaction.rollback()
    engine.dispose()


def test_migration_has_exact_p0_tables_and_can_downgrade():
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(DATABASE_URL)
    names = set(inspect(engine).get_table_names())
    assert {"inbound_events", "outbound_messages", "outbound_receipts"} <= names
    command.downgrade(config, "base")
    names = set(inspect(engine).get_table_names())
    assert not {"inbound_events", "outbound_messages", "outbound_receipts"} & names
    command.upgrade(config, "head")
    engine.dispose()


def test_duplicate_inbound_is_admitted_once(connection):
    store = Store(connection)

    first = store.admit_inbound("wamid-1", "628123456789", "Halo")
    duplicate = store.admit_inbound("wamid-1", "628123456789", "Halo lagi")

    assert first == "pending"
    assert duplicate == "duplicate"
    assert (
        connection.execute(text("select count(*) from inbound_events")).scalar_one()
        == 1
    )


def test_inbound_claim_stale_recovery_and_bounded_failure(connection):
    store = Store(connection)
    store.admit_inbound("wamid-in", "628123456789", "Halo")
    first = store.claim_inbound("worker-old", limit=1)[0]
    assert first["event_id"] == "wamid-in"
    assert store.mark_inbound_done("wamid-in", "wrong") is False
    connection.execute(
        text(
            "UPDATE inbound_events SET lease_until=now()-interval '1 second' WHERE event_id='wamid-in'"
        )
    )
    second = store.claim_inbound("worker-new", limit=1)[0]
    assert second["claim_token"] == "worker-new"
    assert (
        store.mark_inbound_failed(
            "wamid-in", "worker-new", "agent_unavailable", max_attempts=2
        )
        == "DEAD"
    )


def test_outbox_dedupe_is_exact_and_nullable(connection):
    store = Store(connection)

    first = store.enqueue_outbound("628123456789", "Satu", "turn-1:1")
    duplicate = store.enqueue_outbound("628123456789", "Dua", "turn-1:1")
    unkeyed_one = store.enqueue_outbound("628123456789", "Tiga", None)
    unkeyed_two = store.enqueue_outbound("628123456789", "Empat", None)

    assert duplicate is False
    assert all(isinstance(row_id, int) for row_id in (first, unkeyed_one, unkeyed_two))
    assert len({first, unkeyed_one, unkeyed_two}) == 3


def test_early_receipt_reconciles_when_provider_id_arrives(connection):
    store = Store(connection)
    store.record_receipt("provider-1", "DELIVERY_ACK")
    outbound_id = store.enqueue_outbound("628123456789", "Halo", "turn-2:1")

    result = store.mark_accepted(outbound_id, "provider-1")

    assert result == "DELIVERY_ACK"
    row = (
        connection.execute(
            text(
                "select status, provider_message_id, delivered_at from outbound_messages where id=:id"
            ),
            {"id": outbound_id},
        )
        .mappings()
        .one()
    )
    assert row["status"] == "DELIVERY_ACK"
    assert row["provider_message_id"] == "provider-1"
    assert row["delivered_at"] is not None


def test_late_or_duplicate_receipt_never_regresses_delivery(connection):
    store = Store(connection)
    outbound_id = store.enqueue_outbound("628123456789", "Halo", "turn-3:1")
    store.mark_accepted(outbound_id, "provider-2")

    assert store.record_receipt("provider-2", "READ") == "READ"
    assert store.record_receipt("provider-2", "SERVER_ACK") == "READ"
    assert store.record_receipt("provider-2", "READ") == "READ"
    assert store.record_receipt("provider-2", "ERROR") == "ERROR"
    assert store.record_receipt("provider-2", "PLAYED") == "ERROR"


def test_claim_preserves_order_per_phone_and_allows_other_phone(connection):
    store = Store(connection)
    first = store.enqueue_outbound("628111111111", "A1", "a:1")
    second = store.enqueue_outbound("628111111111", "A2", "a:2")
    other = store.enqueue_outbound("628222222222", "B1", "b:1")

    claimed = store.claim_outbound("worker-1", limit=10)

    assert {row["id"] for row in claimed} == {first, other}
    assert second not in {row["id"] for row in claimed}


def test_stale_lease_is_recovered_and_attempts_are_bounded(connection):
    store = Store(connection)
    outbound_id = store.enqueue_outbound("628333333333", "Halo", "c:1")
    assert store.claim_outbound("worker-dead", limit=1)[0]["id"] == outbound_id
    connection.execute(
        text("""
        UPDATE outbound_messages SET lease_until=now() - interval '1 second'
        WHERE id=:id
    """),
        {"id": outbound_id},
    )

    reclaimed = store.claim_outbound("worker-new", limit=1)

    assert reclaimed[0]["id"] == outbound_id
    assert reclaimed[0]["claim_token"] != "worker-dead"


def test_failure_requeues_then_dead_letters_at_max_attempts(connection):
    store = Store(connection)
    outbound_id = store.enqueue_outbound("628444444444", "Halo", "d:1")
    store.claim_outbound("worker-1", limit=1)

    assert (
        store.mark_failed(outbound_id, "worker-1", "transport", max_attempts=2)
        == "QUEUED"
    )
    connection.execute(
        text("UPDATE outbound_messages SET available_at=now() WHERE id=:id"),
        {"id": outbound_id},
    )
    store.claim_outbound("worker-2", limit=1)
    assert (
        store.mark_failed(outbound_id, "worker-2", "transport", max_attempts=2)
        == "DEAD"
    )
