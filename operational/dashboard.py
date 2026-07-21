import json
from json import JSONDecodeError
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from operational.dashboard_security import (
    issue_session,
    mask_phone,
    verify_password,
    verify_request,
)

COOKIE = "marawa_session"
STATIC = Path(__file__).with_name("static")
MAX_JSON_BODY = 65_536
SETTINGS = {
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
TIMEOUTS = {key for key in SETTINGS if key.endswith("_MIN")}


def create_dashboard_app(
    backend,
    evolution,
    *,
    session_secret: str,
    secure_cookie: bool = False,
    allowed_origin: str | None = None,
):
    if len(session_secret) < 32:
        raise ValueError("session secret must be at least 32 characters")
    app = FastAPI()

    @app.exception_handler(ValueError)
    async def invalid_request(request: Request, exc: ValueError):
        return JSONResponse({"detail": "Permintaan tidak valid"}, status_code=422)

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return JSONResponse({"detail": "Kesalahan internal"}, status_code=500)

    @app.middleware("http")
    async def security(request: Request, call_next):
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and allowed_origin
            and request.headers.get("origin") != allowed_origin
        ):
            return Response(status_code=403)
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'",
            }
        )
        return response

    app.mount(
        "/dashboard/static", StaticFiles(directory=STATIC), name="dashboard-static"
    )

    async def json_body(request: Request) -> dict:
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_JSON_BODY:
                raise HTTPException(413, "Permintaan terlalu besar")
            chunks.append(chunk)
        try:
            body = json.loads(b"".join(chunks))
        except (JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(400, "Permintaan tidak valid") from None
        if not isinstance(body, dict):
            raise ValueError("invalid JSON object")
        return body

    def exact(body, fields, required=None):
        if set(body) - set(fields) or not set(required or fields) <= set(body):
            raise ValueError("invalid schema")
        return body

    def audit(actor_id, action, target):
        hook = getattr(backend, "audit", None)
        if callable(hook):
            hook(actor_id, action, target)

    def auth(
        request: Request, *, superadmin=False, mutate=False, allow_temporary=False
    ):
        session = verify_request(
            request.cookies.get(COOKIE, ""),
            request.headers.get("X-CSRF"),
            request.method if mutate else "GET",
            session_secret,
        )
        if not session:
            raise HTTPException(403 if mutate else 401, "Sesi tidak valid")
        current = backend.session_user(session["uid"])
        if (
            not current
            or not current.get("active")
            or current.get("role") != session["role"]
            or current.get("session_version", 1) != session.get("version", 1)
        ):
            raise HTTPException(401, "Sesi tidak valid")
        if current.get("must_change_password") and not allow_temporary:
            raise HTTPException(403, "Password sementara wajib diganti")
        if superadmin and session["role"] != "superadmin":
            raise HTTPException(403, "Khusus superadmin")
        return session

    @app.get("/dashboard", include_in_schema=False)
    def shell():
        return FileResponse(STATIC / "dashboard.html")

    @app.post("/dashboard/api/auth/login")
    async def login(request: Request):
        body = await json_body(request)
        if not body:
            raise HTTPException(401, "Kredensial tidak valid")
        exact(body, {"username", "password"})
        if not isinstance(body["username"], str) or not isinstance(
            body["password"], str
        ):
            raise ValueError("invalid credentials schema")
        user = backend.authenticate(body["username"])
        if (
            not user
            or not user.get("active")
            or not verify_password(body["password"], user["password_hash"])
        ):
            audit(None, "dashboard.login.failure", body["username"])
            raise HTTPException(401, "Kredensial tidak valid")
        audit(user["id"], "dashboard.login.success", str(user["id"]))
        token, csrf = issue_session(
            user["id"],
            user["role"],
            session_secret,
            version=user.get("session_version", 1),
        )
        response = Response(
            content='{"csrf":"' + csrf + '"}', media_type="application/json"
        )
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=secure_cookie,
            samesite="lax",
            max_age=43200,
        )
        return response

    @app.get("/dashboard/api/auth/me")
    def me(request: Request):
        user = auth(request, allow_temporary=True)
        current = backend.session_user(user["uid"])
        return {
            "id": user["uid"],
            "role": user["role"],
            "must_change_password": current.get("must_change_password", False),
        }

    @app.post("/dashboard/api/auth/logout", status_code=204)
    def logout(request: Request):
        user = auth(request, mutate=True, allow_temporary=True)
        audit(user["uid"], "dashboard.logout", str(user["uid"]))
        response = Response(status_code=204)
        response.delete_cookie(COOKIE)
        return response

    @app.post("/dashboard/api/auth/change-password")
    async def change_password(request: Request):
        user = auth(request, mutate=True, allow_temporary=True)
        body = exact(await json_body(request), {"current_password", "password"})
        backend.change_password(user["uid"], body, actor_id=user["uid"])
        response = Response(status_code=204)
        response.delete_cookie(COOKIE)
        return response

    @app.get("/dashboard/api/handover")
    def queue(request: Request):
        user = auth(request)
        return [
            {
                **row,
                "phone": row["phone"]
                if user["role"] == "superadmin"
                else mask_phone(row["phone"]),
            }
            for row in backend.list_handover()
        ]

    def action(request, action_name, code, body):
        user = auth(request, mutate=True)
        if action_name == "claim":
            exact(body, set())
        elif action_name in {"release", "resolve"}:
            exact(body, {"generation"})
            if isinstance(body["generation"], bool) or not isinstance(
                body["generation"], int
            ):
                raise ValueError("invalid generation")
        else:
            exact(body, {"generation", "message"})
            if (
                isinstance(body["generation"], bool)
                or not isinstance(body["generation"], int)
                or not isinstance(body["message"], str)
            ):
                raise ValueError("invalid send")
        return backend.handover_action(action_name, code, user["uid"], body)

    @app.post("/dashboard/api/handover/{code}/claim")
    async def claim(code: str, request: Request):
        return action(request, "claim", code, await json_body(request))

    @app.post("/dashboard/api/handover/{code}/release")
    async def release(code: str, request: Request):
        return action(request, "release", code, await json_body(request))

    @app.post("/dashboard/api/handover/{code}/resolve")
    async def resolve(code: str, request: Request):
        return action(request, "resolve", code, await json_body(request))

    @app.post("/dashboard/api/handover/{code}/send")
    async def send(code: str, request: Request):
        return action(request, "send", code, await json_body(request))

    @app.get("/dashboard/api/users")
    def users(request: Request):
        auth(request, superadmin=True)
        return backend.list_users()

    @app.post("/dashboard/api/users", status_code=201)
    async def create_user(request: Request):
        user = auth(request, superadmin=True, mutate=True)
        body = exact(await json_body(request), {"username", "role", "password"})
        if not all(isinstance(body[key], str) for key in body):
            raise ValueError("invalid user")
        return backend.create_user(body, actor_id=user["uid"])

    @app.post("/dashboard/api/users/{user_id}/reset-password")
    async def reset_password(user_id: int, request: Request):
        user = auth(request, superadmin=True, mutate=True)
        body = exact(await json_body(request), {"password"})
        return backend.reset_password(user_id, body, actor_id=user["uid"])

    @app.patch("/dashboard/api/users/{user_id}")
    async def set_user_active(user_id: int, request: Request):
        user = auth(request, superadmin=True, mutate=True)
        body = exact(await json_body(request), {"active"})
        return backend.set_user_active(user_id, body, actor_id=user["uid"])

    @app.get("/dashboard/api/knowledge")
    def knowledge(request: Request):
        auth(request, superadmin=True)
        return backend.list_knowledge()

    @app.put("/dashboard/api/knowledge/{key}")
    async def update_knowledge(key: str, request: Request):
        user = auth(request, superadmin=True, mutate=True)
        body = exact(
            await json_body(request), {"title", "content", "source_url", "status"}
        )
        if (
            not isinstance(body["title"], str)
            or not isinstance(body["content"], str)
            or body["source_url"] is not None
            and not isinstance(body["source_url"], str)
            or body["status"] not in {"DUMMY", "VERIFIED"}
        ):
            raise ValueError("invalid knowledge")
        return backend.update_knowledge(key, body, actor_id=user["uid"])

    @app.get("/dashboard/api/settings")
    def settings(request: Request):
        auth(request, superadmin=True)
        return backend.get_settings()

    @app.put("/dashboard/api/settings")
    async def set_settings(request: Request):
        user = auth(request, superadmin=True, mutate=True)
        body = await json_body(request)
        if not body or set(body) - SETTINGS:
            raise ValueError("invalid settings")
        for key, value in body.items():
            if key in TIMEOUTS and (
                isinstance(value, bool) or not isinstance(value, int)
            ):
                raise ValueError("invalid timeout")
            if key in {"BOT_ENABLED", "HANDOVER_REBROADCAST"} and not isinstance(
                value, bool
            ):
                raise ValueError("invalid boolean")
            if key == "SERVICE_HOURS" and not isinstance(value, (dict, list, str)):
                raise ValueError("invalid service hours")
        return backend.set_settings(body, actor_id=user["uid"])

    async def evolution_call(operation):
        try:
            result = await operation()
        except httpx.HTTPError:
            raise HTTPException(502, "Layanan Evolution tidak tersedia") from None
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(502, "Layanan Evolution tidak tersedia")
        return result

    @app.get("/dashboard/api/ops/evolution/status")
    async def status(request: Request):
        auth(request, superadmin=True)
        return await evolution_call(evolution.connection_status)

    @app.post("/dashboard/api/ops/evolution/qr")
    async def qr(request: Request):
        user = auth(request, superadmin=True, mutate=True)
        result = await evolution_call(evolution.pairing_qr)
        audit(user["uid"], "dashboard.evolution.qr", "evolution")
        return result

    @app.post("/dashboard/api/ops/evolution/logout")
    async def evolution_logout(request: Request):
        user = auth(request, superadmin=True, mutate=True)
        result = await evolution_call(evolution.logout)
        audit(user["uid"], "dashboard.evolution.logout", "evolution")
        return result

    return app
