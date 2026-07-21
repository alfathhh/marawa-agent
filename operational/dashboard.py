from pathlib import Path

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

    def auth(request: Request, *, superadmin=False, mutate=False):
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
        ):
            raise HTTPException(401, "Sesi tidak valid")
        if superadmin and session["role"] != "superadmin":
            raise HTTPException(403, "Khusus superadmin")
        return session

    @app.get("/dashboard", include_in_schema=False)
    def shell():
        return FileResponse(STATIC / "dashboard.html")

    @app.post("/dashboard/api/auth/login")
    async def login(request: Request):
        body = await request.json()
        user = backend.authenticate(body.get("username"))
        if (
            not user
            or not user.get("active")
            or not verify_password(body.get("password", ""), user["password_hash"])
        ):
            raise HTTPException(401, "Kredensial tidak valid")
        token, csrf = issue_session(user["id"], user["role"], session_secret)
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
        user = auth(request)
        return {"id": user["uid"], "role": user["role"]}

    @app.post("/dashboard/api/auth/logout", status_code=204)
    def logout(request: Request):
        auth(request, mutate=True)
        response = Response(status_code=204)
        response.delete_cookie(COOKIE)
        return response

    @app.get("/dashboard/api/handover")
    def queue(request: Request):
        user = auth(request)
        rows = backend.list_handover()
        return [
            {
                **row,
                "phone": row["phone"]
                if user["role"] == "superadmin"
                else mask_phone(row["phone"]),
            }
            for row in rows
        ]

    def action(request, action, code, body):
        user = auth(request, mutate=True)
        return backend.handover_action(action, code, user["uid"], body)

    @app.post("/dashboard/api/handover/{code}/claim")
    async def claim(code: str, request: Request):
        return action(request, "claim", code, await request.json())

    @app.post("/dashboard/api/handover/{code}/release")
    async def release(code: str, request: Request):
        return action(request, "release", code, await request.json())

    @app.post("/dashboard/api/handover/{code}/resolve")
    async def resolve(code: str, request: Request):
        return action(request, "resolve", code, await request.json())

    @app.post("/dashboard/api/handover/{code}/send")
    async def send(code: str, request: Request):
        return action(request, "send", code, await request.json())

    @app.get("/dashboard/api/users")
    def users(request: Request):
        auth(request, superadmin=True)
        return backend.list_users()

    @app.post("/dashboard/api/users", status_code=201)
    async def create_user(request: Request):
        auth(request, superadmin=True, mutate=True)
        return backend.create_user(await request.json())

    @app.get("/dashboard/api/settings")
    def settings(request: Request):
        auth(request, superadmin=True)
        return backend.get_settings()

    @app.put("/dashboard/api/settings")
    async def set_settings(request: Request):
        auth(request, superadmin=True, mutate=True)
        return backend.set_settings(await request.json())

    @app.get("/dashboard/api/ops/evolution/status")
    async def status(request: Request):
        auth(request, superadmin=True)
        return await evolution.connection_status()

    @app.post("/dashboard/api/ops/evolution/qr")
    async def qr(request: Request):
        auth(request, superadmin=True, mutate=True)
        return await evolution.pairing_qr()

    @app.post("/dashboard/api/ops/evolution/logout")
    async def evolution_logout(request: Request):
        auth(request, superadmin=True, mutate=True)
        return await evolution.logout()

    return app
