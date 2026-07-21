from __future__ import annotations

from sqlalchemy import text

from operational.evolution import advance_delivery


class Store:
    def __init__(self, connection):
        self.connection = connection

    def admit_inbound(self, event_id: str, phone: str, body: str) -> str:
        row = self.connection.execute(text("""
            INSERT INTO inbound_events (event_id, phone, body)
            VALUES (:event_id, :phone, :body)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id
        """), {"event_id": event_id, "phone": phone, "body": body}).first()
        return "pending" if row else "duplicate"

    def enqueue_outbound(self, phone: str, body: str, dedupe_key: str | None):
        row = self.connection.execute(text("""
            INSERT INTO outbound_messages (phone, body, dedupe_key)
            VALUES (:phone, :body, :dedupe_key)
            ON CONFLICT (dedupe_key) DO NOTHING
            RETURNING id
        """), {"phone": phone, "body": body, "dedupe_key": dedupe_key}).first()
        return row[0] if row else False

    def mark_accepted(self, outbound_id: int, provider_message_id: str | None):
        status = "ACCEPTED"
        if provider_message_id:
            receipt = self.connection.execute(text("""
                SELECT status FROM outbound_receipts
                WHERE provider_message_id=:provider_message_id
            """), {"provider_message_id": provider_message_id}).first()
            if receipt:
                status = advance_delivery(status, receipt[0])
        delivered = status in {"DELIVERY_ACK", "READ", "PLAYED"}
        self.connection.execute(text("""
            UPDATE outbound_messages
            SET status=:status, provider_message_id=:provider_message_id,
                accepted_at=now(), delivered_at=CASE WHEN :delivered THEN now() ELSE delivered_at END,
                updated_at=now()
            WHERE id=:outbound_id
        """), {"status": status, "provider_message_id": provider_message_id,
                 "delivered": delivered, "outbound_id": outbound_id})
        return status

    def record_receipt(self, provider_message_id: str, incoming: str):
        row = self.connection.execute(text("""
            SELECT id, status FROM outbound_messages
            WHERE provider_message_id=:provider_message_id FOR UPDATE
        """), {"provider_message_id": provider_message_id}).first()
        if not row:
            existing = self.connection.execute(text("""
                SELECT status FROM outbound_receipts
                WHERE provider_message_id=:provider_message_id FOR UPDATE
            """), {"provider_message_id": provider_message_id}).first()
            status = advance_delivery(existing[0], incoming) if existing else incoming
            self.connection.execute(text("""
                INSERT INTO outbound_receipts (provider_message_id, status)
                VALUES (:provider_message_id, :status)
                ON CONFLICT (provider_message_id) DO UPDATE
                SET status=EXCLUDED.status, updated_at=now()
            """), {"provider_message_id": provider_message_id, "status": status})
            return status
        status = advance_delivery(row[1], incoming)
        delivered = status in {"DELIVERY_ACK", "READ", "PLAYED"}
        self.connection.execute(text("""
            UPDATE outbound_messages
            SET status=:status,
                delivered_at=CASE WHEN :delivered AND delivered_at IS NULL THEN now() ELSE delivered_at END,
                updated_at=now()
            WHERE id=:outbound_id
        """), {"status": status, "delivered": delivered, "outbound_id": row[0]})
        return status
