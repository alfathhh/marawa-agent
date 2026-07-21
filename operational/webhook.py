from __future__ import annotations

import hmac
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from operational.evolution import parse_event


def create_webhook_app(
    store,
    *,
    webhook_secret: str,
    instance: str,
    production: bool = False,
    max_body_bytes: int = 262_144,
):
    if len(webhook_secret) < 32:
        raise ValueError("WEBHOOK_SECRET must be at least 32 characters")
    app = FastAPI()

    @app.post("/webhook")
    async def webhook(request: Request):
        supplied = request.headers.get("X-Webhook-Secret", "")
        if not hmac.compare_digest(supplied.encode(), webhook_secret.encode()):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_body_bytes:
                    return JSONResponse({"detail": "Payload too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > max_body_bytes:
                return JSONResponse({"detail": "Payload too large"}, status_code=413)
            body.extend(chunk)
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"detail": "JSON object required"}, status_code=422)
        if production and payload.get("instance") != instance:
            return JSONResponse({"detail": "Instance mismatch"}, status_code=403)
        event = parse_event(payload)
        if event is None:
            return {"status": "ignored"}
        if event["kind"] == "delivery":
            status = store.record_receipt(event["provider_message_id"], event["status"])
            return {"status": status}
        status = store.admit_inbound(event["event_id"], event["phone"], event["text"])
        return JSONResponse({"status": status}, status_code=202)

    return app
