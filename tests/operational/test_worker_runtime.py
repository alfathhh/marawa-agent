import asyncio

from operational.worker import knowledge_reply


def test_dummy_runtime_never_invents_statistics():
    async def kb():
        return [
            {
                "title": "Layanan PST",
                "content": "Konten dummy.",
                "status": "DUMMY",
                "source_url": None,
            }
        ]

    data = asyncio.run(
        knowledge_reply("berapa jumlah penduduk 2025?", "628123456789", kb)
    )

    assert "belum dapat memberikan angka" in data["text"]
    assert data["sources"] == []
    assert "Konten dummy" not in data["text"]


def test_dummy_runtime_labels_service_content():
    async def kb():
        return [
            {
                "title": "Layanan PST",
                "content": "Konsultasi diarahkan ke Buku Tamu.",
                "status": "DUMMY",
                "source_url": "https://s.bps.go.id/tamu1306",
            }
        ]

    data = asyncio.run(
        knowledge_reply("bagaimana konsultasi statistik?", "628123456789", kb)
    )

    assert "DUMMY / BELUM DIVERIFIKASI" in data["text"]
    assert data["sources"] == [
        {"title": "Layanan PST", "url": "https://s.bps.go.id/tamu1306"}
    ]
