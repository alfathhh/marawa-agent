import asyncio
import os
import secrets

import httpx
from sqlalchemy import create_engine, text

from operational.delivery import deliver_batch
from operational.evolution import EvolutionClient
from operational.inbound import process_batch
from operational.persistence import Store


def _asks_for_data(question: str) -> bool:
    words = question.casefold().split()
    return any(
        word in words
        for word in (
            "data",
            "jumlah",
            "berapa",
            "persen",
            "persentase",
            "penduduk",
            "kemiskinan",
            "pengangguran",
        )
    )


async def knowledge_reply(question, phone, load_knowledge):
    if _asks_for_data(question):
        return {
            "text": "Saya belum dapat memberikan angka karena runtime Web API BPS belum terhubung. Saya tidak akan menebak data. Silakan minta bantuan petugas atau gunakan Buku Tamu: https://s.bps.go.id/tamu1306",
            "sources": [],
        }
    rows = await load_knowledge()
    usable = [row for row in rows if row.get("content")]
    if not usable:
        return {
            "text": "Informasi belum tersedia. Silakan gunakan Buku Tamu: https://s.bps.go.id/tamu1306",
            "sources": [],
        }
    row = next((item for item in usable if item.get("status") == "VERIFIED"), usable[0])
    label = "DUMMY / BELUM DIVERIFIKASI\n\n" if row.get("status") == "DUMMY" else ""
    sources = (
        [{"title": row["title"], "url": row["source_url"]}]
        if row.get("source_url")
        else []
    )
    return {"text": label + row["content"], "sources": sources}


async def main():
    required = (
        "DATABASE_URL",
        "EVOLUTION_API_URL",
        "EVOLUTION_API_KEY",
        "EVOLUTION_INSTANCE",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing worker configuration: " + ", ".join(missing))
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    connection = engine.connect()
    store = Store(connection)

    async def load_knowledge():
        rows = connection.execute(
            text(
                "SELECT title, content, status, source_url FROM knowledge_base ORDER BY key"
            )
        ).mappings()
        return [dict(row) for row in rows]

    async def runtime(question, phone):
        return await knowledge_reply(question, phone, load_knowledge)

    async with httpx.AsyncClient(
        base_url=os.environ["EVOLUTION_API_URL"], timeout=30
    ) as http:
        evolution = EvolutionClient(
            http, os.environ["EVOLUTION_API_KEY"], os.environ["EVOLUTION_INSTANCE"]
        )
        while True:
            token = secrets.token_hex(16)
            try:
                inbound = await process_batch(store, runtime, token)
                outbound = await deliver_batch(store, evolution, token)
                connection.commit()
            except Exception:
                connection.rollback()
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(
                    0 if any((*inbound.values(), *outbound.values())) else 1
                )


if __name__ == "__main__":
    asyncio.run(main())
