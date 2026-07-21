from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

GUESTBOOK_URL = "https://s.bps.go.id/tamu1306"


class HandoverStore:
    def __init__(self, connection):
        self.connection = connection

    def request(
        self,
        user_phone: str,
        deadline_at: datetime | None = None,
    ) -> int:
        row = self.connection.execute(
            text("""
            INSERT INTO handovers (user_phone, deadline_at)
            VALUES (:user_phone, :deadline_at)
            ON CONFLICT (user_phone)
                WHERE status IN ('PENDING','ACTIVE')
            DO UPDATE SET user_phone=EXCLUDED.user_phone
            RETURNING id
        """),
            {
                "user_phone": user_phone,
                "deadline_at": deadline_at,
            },
        ).one()
        return row[0]

    def claim(self, handover_id: int, owner_id: str) -> dict | None:
        row = (
            self.connection.execute(
                text("""
            UPDATE handovers
            SET state='ADMIN_ACTIVE', status='ACTIVE', owner_id=:owner_id,
                generation=generation+1, updated_at=now()
            WHERE id=:id AND status='PENDING' AND owner_id IS NULL
            RETURNING id, owner_id, generation
        """),
                {"id": handover_id, "owner_id": owner_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def release(self, handover_id: int, owner_id: str, generation: int) -> bool:
        row = self.connection.execute(
            text("""
            UPDATE handovers
            SET state='HANDOVER_PENDING', status='PENDING', owner_id=NULL,
                generation=generation+1, updated_at=now()
            WHERE id=:id AND status='ACTIVE' AND owner_id=:owner_id
                AND generation=:generation
            RETURNING id
        """),
            {
                "id": handover_id,
                "owner_id": owner_id,
                "generation": generation,
            },
        ).first()
        return row is not None

    def resolve(self, handover_id: int, owner_id: str, generation: int) -> bool:
        row = self.connection.execute(
            text("""
            UPDATE handovers
            SET state='BOT_ACTIVE', status='RESOLVED', owner_id=NULL,
                generation=generation+1, updated_at=now()
            WHERE id=:id AND status='ACTIVE' AND owner_id=:owner_id
                AND generation=:generation
            RETURNING id
        """),
            {
                "id": handover_id,
                "owner_id": owner_id,
                "generation": generation,
            },
        ).first()
        return row is not None

    def fail(self, handover_id: int) -> dict | None:
        row = self.connection.execute(
            text("""
            UPDATE handovers
            SET state='BOT_ACTIVE', status='FAILED', owner_id=NULL,
                generation=generation+1, fallback_url=:fallback_url,
                updated_at=now()
            WHERE id=:id AND status IN ('PENDING','ACTIVE')
            RETURNING id
        """),
            {"id": handover_id, "fallback_url": GUESTBOOK_URL},
        ).first()
        return {"id": row[0], "guestbook_url": GUESTBOOK_URL} if row else None

    def process_deadlines(self, limit: int = 100) -> list[dict]:
        rows = self.connection.execute(
            text("""
            WITH due AS (
                SELECT id FROM handovers
                WHERE status='PENDING' AND deadline_at <= now()
                ORDER BY deadline_at, id
                FOR UPDATE SKIP LOCKED LIMIT :limit
            )
            UPDATE handovers h
            SET state='BOT_ACTIVE', status='EXPIRED', owner_id=NULL,
                generation=h.generation+1, fallback_url=:fallback_url,
                updated_at=now()
            FROM due WHERE h.id=due.id
            RETURNING h.id
        """),
            {"limit": limit, "fallback_url": GUESTBOOK_URL},
        ).all()
        return [{"id": row[0], "guestbook_url": GUESTBOOK_URL} for row in rows]
