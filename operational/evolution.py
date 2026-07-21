from __future__ import annotations

import base64
import binascii

import httpx

_STATUS = {
    0: "ERROR",
    1: "PENDING",
    2: "SERVER_ACK",
    3: "DELIVERY_ACK",
    4: "READ",
    5: "PLAYED",
}
_PROGRESS = {
    "QUEUED": 0,
    "SENDING": 1,
    "ACCEPTED": 2,
    "PENDING": 2,
    "SERVER_ACK": 3,
    "DELIVERY_ACK": 4,
    "READ": 5,
    "PLAYED": 6,
}


def parse_event(payload):
    if not isinstance(payload, dict):
        return None
    if payload.get("event") == "messages.upsert":
        return _parse_inbound(payload.get("data"))
    if payload.get("event") == "messages.update":
        return _parse_delivery(payload.get("data"))
    return None


def _parse_inbound(data):
    if not isinstance(data, dict):
        return None
    key = data.get("key")
    message = data.get("message")
    if not isinstance(key, dict) or not isinstance(message, dict) or key.get("fromMe"):
        return None
    jid = key.get("remoteJid")
    event_id = key.get("id")
    if not isinstance(jid, str) or not jid.endswith("@s.whatsapp.net"):
        return None
    phone = jid.removesuffix("@s.whatsapp.net")
    if not phone.isdigit() or not 8 <= len(phone) <= 16 or not isinstance(event_id, str):
        return None
    extended = message.get("extendedTextMessage")
    text = message.get("conversation")
    if text is None and isinstance(extended, dict):
        text = extended.get("text")
    if not isinstance(text, str) or not text or len(text) > 8_000:
        return None
    name = data.get("pushName")
    return {
        "kind": "inbound",
        "event_id": event_id,
        "phone": phone,
        "name": name[:255] if isinstance(name, str) else None,
        "text": text,
    }


def _parse_delivery(data):
    if not isinstance(data, dict):
        return None
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    update = data.get("update") if isinstance(data.get("update"), dict) else {}
    message_id = data.get("keyId") or data.get("messageId") or key.get("id") or data.get("id")
    raw_status = data.get("status", update.get("status"))
    status = _STATUS.get(raw_status, str(raw_status).strip().upper())
    if not isinstance(message_id, str) or status not in {*_PROGRESS, "ERROR"}:
        return None
    return {"kind": "delivery", "provider_message_id": message_id, "status": status}


def advance_delivery(current, incoming):
    if current == "ERROR" or incoming == "ERROR":
        return "ERROR"
    if incoming not in _PROGRESS:
        return current
    return incoming if _PROGRESS[incoming] > _PROGRESS.get(current, -1) else current


class EvolutionClient:
    def __init__(self, client, api_key: str, instance: str):
        self.client, self.api_key, self.instance = client, api_key, instance

    async def send_text(self, phone: str, text: str):
        if not phone.isdigit() or not 8 <= len(phone) <= 16 or not text:
            return {"error": {"code": "invalid_evolution_request"}}
        try:
            response = await self.client.post(
                f"/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": phone, "text": text},
            )
            response.raise_for_status()
            payload = response.json()
            key = payload.get("key") if isinstance(payload, dict) else None
            message_id = key.get("id") if isinstance(key, dict) else None
        except (httpx.HTTPError, ValueError, TypeError):
            return {"error": {"code": "evolution_unavailable"}}
        return {
            "status": "ACCEPTED",
            "provider_message_id": message_id if isinstance(message_id, str) else None,
        }

    async def connection_status(self):
        try:
            response = await self.client.get(
                f"/instance/connectionState/{self.instance}",
                headers={"apikey": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()
            nested = payload.get("instance") if isinstance(payload, dict) else None
            raw = nested.get("state") if isinstance(nested, dict) else payload.get("state")
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return {"error": {"code": "evolution_unavailable"}}
        state = str(raw or "unknown").casefold()
        normalized = {"open": "connected", "connected": "connected",
                      "close": "disconnected", "closed": "disconnected",
                      "connecting": "connecting"}.get(state, "unknown")
        return {"instance": self.instance, "state": normalized}

    async def pairing_qr(self):
        try:
            response = await self.client.get(
                f"/instance/connect/{self.instance}", headers={"apikey": self.api_key})
            response.raise_for_status()
            payload = response.json()
            candidate = payload.get("base64") if isinstance(payload, dict) else None
            encoded = candidate.split(",", 1)[-1] if isinstance(candidate, str) else ""
            decoded = base64.b64decode(encoded, validate=True)
            qr = ("data:image/png;base64," + encoded
                  if 0 < len(decoded) <= 1_000_000 and decoded.startswith(b"\x89PNG\r\n\x1a\n")
                  else None)
        except (httpx.HTTPError, ValueError, TypeError, binascii.Error):
            return {"error": {"code": "evolution_unavailable"}}
        return {"instance": self.instance, "state": "connecting", "qr": qr}

    async def logout(self):
        try:
            response = await self.client.delete(
                f"/instance/logout/{self.instance}", headers={"apikey": self.api_key})
            response.raise_for_status()
        except httpx.HTTPError:
            return {"error": {"code": "evolution_unavailable"}}
        return {"instance": self.instance, "state": "disconnected"}
