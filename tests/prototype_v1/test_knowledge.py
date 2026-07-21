import asyncio
from pathlib import Path

import httpx
import pytest
import yaml

from prototype_v1.bps_adapter import BPSAdapter
from prototype_v1.knowledge import (
    glossary_search,
    load_documents,
    load_territories,
    no_match_response,
    render_sources,
    search,
)
from prototype_v1.templates import GUESTBOOK_URL, TEMPLATES


GLOSSARY_URL = "https://webapi.bps.go.id/v1/api/glossary"


def client(response):
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response), base_url="https://webapi.bps.go.id")


def test_glossary_returns_documented_fields_without_registering_indicator_value():
    payload = {"data": [{"glossary_id": 4406, "concept": "Penduduk", "indicator_title": "", "definition": "Orang berusia 15 tahun atau lebih.", "unit": ""}]}

    async def run():
        async with client(httpx.Response(200, json=payload)) as http:
            return await glossary_search(http, "penduduk", url=GLOSSARY_URL)

    result = asyncio.run(run())

    assert result == {"found": True, "items": [{"source_ref": "glossary_4406", "concept": "Penduduk", "indicator_title": "", "definition": "Orang berusia 15 tahun atau lebih.", "unit": "", "source_content": "Glosarium Web API BPS", "source_url": "https://webapi.bps.go.id/documentation/#glosarium"}]}
    assert "value_decimal" not in result["items"][0]


def test_adapter_parses_official_glossary_source_envelope():
    adapter = BPSAdapter({"glossary": {
        "status": "OK",
        "data": [{"page": 1}, [{"_source": {
            "id": "4406",
            "konsep": "Agama",
            "definisi": "Keyakinan terhadap Tuhan Yang Maha Esa.",
            "judulIndikator": "",
            "satuan": "",
            "sumberKonten": "Metadata Management System",
        }}]],
    }}, app_env="test")

    result = adapter.glossary("agama")

    assert result["found"] is True
    assert result["items"][0]["source_ref"] == "glossary_4406"
    assert result["items"][0]["concept"] == "Agama"
    assert result["items"][0]["definition"] == "Keyakinan terhadap Tuhan Yang Maha Esa."


@pytest.mark.parametrize("query", ["", "x" * 501, 2])
def test_glossary_rejects_invalid_query_without_request(query):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await glossary_search(http, query, url=GLOSSARY_URL)

    assert asyncio.run(run()) == {"error": {"code": "invalid_query"}}
    assert calls == 0


@pytest.mark.parametrize("response", [httpx.Response(500, text="SECRET RAW BODY"), httpx.Response(401, text="SECRET RAW BODY"), httpx.Response(429, text="SECRET RAW BODY")])
def test_glossary_http_failure_is_safe_and_not_cached(response):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return response

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            first = await glossary_search(http, "penduduk", url=GLOSSARY_URL)
            second = await glossary_search(http, "penduduk", url=GLOSSARY_URL)
            return first, second

    first, second = asyncio.run(run())

    assert first == second == {"error": {"code": "glossary_unavailable"}}
    assert "SECRET" not in str(first)
    assert calls == (2 if response.status_code == 401 else 4)


@pytest.mark.parametrize("status, expected_calls", [(401, 1), (429, 2), (500, 2)])
def test_glossary_retries_only_retryable_status_once(status, expected_calls):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(status)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await glossary_search(http, "penduduk", url=GLOSSARY_URL)

    assert asyncio.run(run()) == {"error": {"code": "glossary_unavailable"}}
    assert calls == expected_calls


@pytest.mark.parametrize("payload", [{"data": "bad"}, {"data": [{"glossary_id": 1, "concept": "x"}]}, [1]])
def test_glossary_rejects_malformed_success(payload):
    async def run():
        async with client(httpx.Response(200, json=payload)) as http:
            return await glossary_search(http, "x", url=GLOSSARY_URL)

    assert asyncio.run(run()) == {"error": {"code": "glossary_schema_error"}}


def write_yaml(path, **overrides):
    data = {"source_key": "pst_services", "title": "Layanan PST", "source_url": "https://pst.bps.go.id", "verified": True, "verified_by": "Reviewer", "verified_at": "2026-07-21", "sections": [{"heading": "Konsultasi Statistik", "text": "Layanan konsultasi tersedia 8 jam.", "aliases": ["konsultasi"]}]}
    data.update(overrides)
    path.write_text(yaml.safe_dump(data, allow_unicode=True))


def test_kb_loads_verified_yaml_and_markdown_then_ranks_at_most_four(tmp_path):
    for index in range(5):
        write_yaml(tmp_path / f"{index}.yaml", source_key=f"source_{index}")
    (tmp_path / "extra.md").write_text("---\nsource_key: markdown\ntitle: Panduan PST\nsource_url: https://pst.bps.go.id\nverified: true\nverified_by: Reviewer\nverified_at: 2026-07-21\n---\n## Konsultasi Statistik\nLayanan konsultasi tersedia.")

    result = search(load_documents(tmp_path), "konsultasi statistik", limit=99)

    assert result["found"] is True
    assert len(result["chunks"]) == 4
    assert all(chunk["verified_by"] == "Reviewer" for chunk in result["chunks"])


def test_kb_ignores_unverified_document(tmp_path):
    write_yaml(tmp_path / "draft.yaml", verified=False, verified_by="", verified_at="")

    assert load_documents(tmp_path) == []


@pytest.mark.parametrize("change", [{"extra": "closed"}, {"sections": [{"heading": "x", "text": "y", "unknown": 1}]}, {"source_url": "http://evil.example"}, {"verified_by": ""}])
def test_kb_rejects_invalid_or_open_metadata(tmp_path, change):
    write_yaml(tmp_path / "bad.yaml", **change)

    with pytest.raises(ValueError, match="kb_schema_error"):
        load_documents(tmp_path)


def test_unsigned_territory_registry_accepts_nothing(tmp_path):
    path = tmp_path / "territories.yaml"
    path.write_text(yaml.safe_dump({"verified": False, "verified_by": "", "verified_at": "", "territories": [{"code": "1306010", "label": "Kecamatan Batang Anai", "ancestor": "1306"}]}))

    registry = load_territories(path)

    assert registry.accepts("1306010", "Kecamatan Batang Anai") is False


def test_verified_territory_requires_exact_code_label_and_ancestor(tmp_path):
    path = tmp_path / "territories.yaml"
    path.write_text(yaml.safe_dump({"verified": True, "verified_by": "Reviewer", "verified_at": "2026-07-21", "territories": [{"code": "1306010", "label": "Kecamatan Batang Anai", "ancestor": "1306"}]}))

    registry = load_territories(path)

    assert registry.accepts("1306010", "Kecamatan Batang Anai") is True
    assert registry.accepts("1306010", "Batang Anai") is False
    assert registry.accepts("130601", "Kecamatan Batang Anai") is False


def test_conflict_keeps_sources_separate_and_offers_admin():
    items = [{"title": "Glosarium Web API BPS", "context": "Penduduk", "definition": "Definisi A", "source_url": "https://webapi.bps.go.id/documentation/#glosarium"}, {"title": "Knowledge base PST", "heading": "Penduduk", "text": "Definisi B", "source_url": "https://pst.bps.go.id"}]

    result = render_sources(items, conflict=True)

    assert result["text"].count("Sumber:") == 2
    assert "Definisi A\nSumber:" in result["text"]
    assert "Definisi B\nSumber:" in result["text"]
    assert result["actions"] == [{"id": "act_admin", "label": "Hubungi admin (simulasi)", "value": "offer_admin", "kind": "handover"}]


def test_no_match_is_exact_template_with_admin_and_guestbook():
    result = no_match_response()

    assert result == {"text": TEMPLATES["NO_OFFICIAL_SOURCE"], "actions": [{"id": "act_admin", "label": "Hubungi admin (simulasi)", "value": "offer_admin", "kind": "handover"}, {"id": "act_guestbook", "label": "Buku Tamu", "value": GUESTBOOK_URL, "kind": "link"}]}
    assert "definition" not in result


def test_no_code_references_sirusa():
    source = Path("prototype_v1/knowledge.py").read_text().casefold()

    assert "sirusa" not in source
