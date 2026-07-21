from contextlib import asynccontextmanager
import asyncio

import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine

from operational.dashboard import create_dashboard_app
from operational.dashboard_backend import DashboardBackend
from operational.evolution import EvolutionClient
from operational.persistence import Store
from operational.webhook import create_webhook_app


def create_app(
    *,
    database_url: str,
    evolution_url: str,
    evolution_key: str,
    evolution_instance: str,
    webhook_secret: str,
    session_secret: str,
    allowed_origin: str,
    production: bool = False,
):
    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    http = httpx.AsyncClient(base_url=evolution_url, timeout=30)
    evolution = EvolutionClient(http, evolution_key, evolution_instance)
    backend = DashboardBackend(connection)
    store = Store(connection)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await http.aclose()
        connection.close()
        engine.dispose()

    app = FastAPI(lifespan=lifespan)
    webhook = create_webhook_app(
        store,
        webhook_secret=webhook_secret,
        instance=evolution_instance,
        production=production,
    )
    dashboard = create_dashboard_app(
        backend,
        evolution,
        session_secret=session_secret,
        secure_cookie=production,
        allowed_origin=allowed_origin,
    )
    app.mount("/webhooks", webhook)
    app.mount("/", dashboard)

    transaction_lock = asyncio.Lock()

    @app.middleware("http")
    async def transaction(request, call_next):
        # ponytail: one process/worker; move to connection-per-request before multi-replica.
        async with transaction_lock:
            try:
                response = await call_next(request)
                if response.status_code < 400:
                    connection.commit()
                else:
                    connection.rollback()
                return response
            except Exception:
                connection.rollback()
                raise

    return app
