from __future__ import annotations

import re

from sqlalchemy import text

from operational.dashboard_security import hash_password
from operational.handover import HandoverStore

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
_ROLES = {"petugas", "superadmin"}
_SETTINGS = {
    "BOT_ENABLED",
    "SERVICE_HOURS",
    "ADMIN_CLAIM_TIMEOUT_MIN",
    "ADMIN_FIRST_REPLY_TIMEOUT_MIN",
    "ADMIN_IDLE_RELEASE_MIN",
    "USER_IDLE_WARNING_MIN",
    "USER_IDLE_CLOSE_MIN",
    "USER_IDLE_IN_HANDOVER_MIN",
    "HANDOVER_REBROADCAST",
}
_TIMEOUTS = {key for key in _SETTINGS if key.endswith("_MIN")}


class DashboardBackend:
    def __init__(self, connection):
        self.connection = connection
        self.handovers = HandoverStore(connection)

    def _audit(self, actor_id: int | None, action: str, target: str) -> None:
        self.connection.execute(
            text(
                "INSERT INTO audit_log (actor_id, action, target) VALUES (:actor, :action, :target)"
            ),
            {"actor": actor_id, "action": action, "target": target},
        )

    def authenticate(self, username: str) -> dict | None:
        if not isinstance(username, str):
            return None
        row = (
            self.connection.execute(
                text(
                    "SELECT id, username, password_hash, role, active FROM dashboard_users WHERE username=:username"
                ),
                {"username": username},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def session_user(self, user_id: int) -> dict | None:
        row = (
            self.connection.execute(
                text("SELECT id, role, active FROM dashboard_users WHERE id=:id"),
                {"id": user_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        rows = self.connection.execute(
            text("SELECT id, username, role, active FROM dashboard_users ORDER BY id")
        ).mappings()
        return [dict(row) for row in rows]

    def create_user(self, body: dict, actor_id: int | None = None) -> dict:
        if not isinstance(body, dict):
            raise ValueError("invalid user")
        username, role = body.get("username"), body.get("role")
        if not isinstance(username, str) or not _USERNAME.fullmatch(username):
            raise ValueError("invalid username")
        if role not in _ROLES:
            raise ValueError("invalid role")
        password_hash = hash_password(body.get("password"))
        row = (
            self.connection.execute(
                text("""
                INSERT INTO dashboard_users (username, password_hash, role)
                VALUES (:username, :password_hash, :role)
                RETURNING id, username, role, active
            """),
                {"username": username, "password_hash": password_hash, "role": role},
            )
            .mappings()
            .one()
        )
        self._audit(actor_id, "user.create", str(row["id"]))
        return dict(row)

    def get_settings(self) -> dict:
        rows = self.connection.execute(
            text("SELECT key, value FROM settings WHERE key = ANY(:keys)"),
            {"keys": list(_SETTINGS)},
        )
        return {key: value for key, value in rows}

    def set_settings(self, body: dict, actor_id: int | None = None) -> dict:
        if not isinstance(body, dict) or not body or set(body) - _SETTINGS:
            raise ValueError("invalid settings")
        for key in set(body) & _TIMEOUTS:
            value = body[key]
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= 1440
            ):
                raise ValueError("invalid timeout")
        for key, value in body.items():
            self.connection.execute(
                text("""
                    INSERT INTO settings (key, value) VALUES (:key, CAST(:value AS jsonb))
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
                """),
                {"key": key, "value": str(value)},
            )
            self._audit(actor_id, "settings.set", key)
        return self.get_settings()

    def list_handover(self) -> list[dict]:
        rows = self.connection.execute(
            text("""
            SELECT id, user_phone AS phone, state, status, owner_id, generation,
                   deadline_at, created_at, updated_at
            FROM handovers WHERE status IN ('PENDING','ACTIVE') ORDER BY created_at, id
        """)
        ).mappings()
        return [dict(row) for row in rows]

    def handover_action(
        self, action: str, code: str, actor_id: int, body: dict
    ) -> dict:
        try:
            handover_id = int(code)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid handover") from exc
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        if action == "claim":
            result = self.handovers.claim(handover_id, str(actor_id))
        elif action in {"release", "resolve"}:
            generation = self._generation(body)
            ok = getattr(self.handovers, action)(handover_id, str(actor_id), generation)
            result = {"ok": True} if ok else None
        elif action == "send":
            result = self._send(handover_id, actor_id, body)
        else:
            raise ValueError("invalid action")
        if result is None:
            raise ValueError("handover conflict")
        self._audit(actor_id, f"handover.{action}", str(handover_id))
        return result

    @staticmethod
    def _generation(body: dict) -> int:
        generation = body.get("generation")
        if (
            isinstance(generation, bool)
            or not isinstance(generation, int)
            or generation < 1
        ):
            raise ValueError("invalid generation")
        return generation

    def _send(self, handover_id: int, actor_id: int, body: dict) -> dict | None:
        generation = self._generation(body)
        message = body.get("message")
        if not isinstance(message, str) or not message.strip() or len(message) > 4096:
            raise ValueError("invalid message")
        row = (
            self.connection.execute(
                text("""
            INSERT INTO outbound_messages (phone, body, dedupe_key)
            SELECT user_phone, :body, :dedupe
            FROM handovers
            WHERE id=:id AND status='ACTIVE' AND owner_id=:owner AND generation=:generation
            ON CONFLICT (dedupe_key) DO UPDATE SET dedupe_key=EXCLUDED.dedupe_key
            RETURNING id, status
        """),
                {
                    "id": handover_id,
                    "owner": str(actor_id),
                    "generation": generation,
                    "body": message.strip(),
                    "dedupe": f"dashboard:{handover_id}:{generation}:{message.strip()}",
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None
