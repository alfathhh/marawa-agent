import secrets
import time
import uuid
from pathlib import Path
from fastapi import FastAPI, Request, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import load_config
from .state import SessionStore
from .intents import ProviderMock, route_intents

APP_NAME = "marawa-prototype-v1"
SERVER_GENERATION = f"boot_{secrets.token_urlsafe(12)}"
CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": CSP,
}
config = load_config()
store = SessionStore(SERVER_GENERATION)
static_dir = Path(__file__).with_name("static")
app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def error(status, code, message, details=None):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
        headers=HEADERS,
    )


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method in {"POST", "DELETE"} and (
        request.headers.get("origin") != config.allowed_origin
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        return error(403, "origin_not_allowed", "Origin tidak diizinkan.")
    r = await call_next(request)
    r.headers.update(HEADERS)
    return r


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/api/prototype/live")
def live():
    return {
        "data": {
            "status": "ok",
            "app": APP_NAME,
            "server_generation": SERVER_GENERATION,
        }
    }


@app.post("/api/prototype/sessions", status_code=201)
def create():
    try:
        s = store.create()
    except RuntimeError:
        return error(429, "session_capacity", "Kapasitas sesi penuh.")
    return {
        "data": {
            "session_id": s.session_id,
            "server_generation": s.server_generation,
            "state_version": 0,
            "created_at": s.created_at.isoformat().replace("+00:00", "Z"),
            "expires_after_idle_seconds": 7200,
        }
    }


@app.get("/api/prototype/sessions/{sid}")
def get(sid: str, x_server_generation: str | None = Header(default=None)):
    try:
        s = store.get(sid, x_server_generation)
    except ValueError:
        return error(
            409,
            "generation_mismatch",
            "Sesi perlu dibuat ulang.",
            {"expected_action": "start_new_session"},
        )
    except TimeoutError:
        return error(
            410,
            "session_expired",
            "Sesi kedaluwarsa.",
            {"expected_action": "start_new_session"},
        )
    if not s:
        return error(404, "session_not_found", "Sesi tidak ditemukan.")
    return {
        "data": {
            "session_id": sid,
            "server_generation": s.server_generation,
            "state_version": s.state_version,
            "status": "active",
            "last_active_at": s.last_active_at.isoformat().replace("+00:00", "Z"),
        }
    }


@app.delete("/api/prototype/sessions/{sid}", status_code=204)
def delete(sid: str, x_server_generation: str | None = Header(default=None)):
    if sid in store.sessions and x_server_generation != SERVER_GENERATION:
        return error(409, "generation_mismatch", "Sesi perlu dibuat ulang.")
    store.delete(sid)
    return None


@app.post("/api/prototype/sessions/{sid}/messages")
async def message(
    sid: str, payload: dict, x_server_generation: str | None = Header(default=None)
):
    try:
        s = store.get(sid, x_server_generation)
    except ValueError:
        return error(409, "generation_mismatch", "Sesi perlu dibuat ulang.")
    except TimeoutError:
        return error(410, "session_expired", "Sesi kedaluwarsa.")
    if not s:
        return error(404, "session_not_found", "Sesi tidak ditemukan.")
    mid, text, version = payload.get("message_id"), payload.get("text"), payload.get("state_version")
    try:
        uuid.UUID(mid)
    except (ValueError, AttributeError, TypeError):
        return error(422, "validation_error", "Pesan tidak valid.", {"field": "message_id"})
    if not isinstance(text, str) or not text.strip() or len(text.strip()) > 8000:
        return error(422, "validation_error", "Pesan tidak valid.", {"field": "text"})
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        return error(422, "validation_error", "Pesan tidak valid.", {"field": "state_version"})
    text = text.strip()
    async with s.lock:
        cached = store.cached(s, mid)
        if cached:
            return cached
        if not store.version_ok(s, version):
            return error(409, "state_version_conflict", "Versi sesi sudah berubah.", {"current_state_version": s.state_version})
        cutoff = time.time() - 3600
        s.turn_timestamps[:] = [stamp for stamp in s.turn_timestamps if stamp >= cutoff]
        if len(s.turn_timestamps) >= 20:
            return error(429, "turn_rate_limited", "Batas percakapan per jam tercapai.", {"retry_after_seconds": 3600})
        s.turn_timestamps.append(time.time())
        routed = route_intents(text, ProviderMock())
        reply = routed.reply or "Permintaan diterima. Sumber resmi dan pilihan terstruktur akan digunakan sesuai cakupan Prototype 1."
        response = {"data": {"session_id": sid, "server_generation": SERVER_GENERATION, "state_version": s.state_version + 1, "turn_status": "completed", "assistant": {"id": "msg_" + secrets.token_urlsafe(8), "text": reply, "actions": [], "sources": [], "provenance": []}}}
        store.append_message(s, store.new_message("user", text, mid))
        store.append_message(s, store.new_message("assistant", reply, response["data"]["assistant"]["id"]))
        return store.commit(s, mid, response)


__all__ = ["app"]
