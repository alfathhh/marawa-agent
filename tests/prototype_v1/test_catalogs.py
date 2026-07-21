import asyncio

import httpx

from prototype_v1.bps_adapter import BPSAdapter
from prototype_v1.catalog_service import (
    add_page,
    new_frame,
    resolve_candidate,
    search_catalogs,
    select_candidate,
)

URL = "https://padangpariamankab.bps.go.id/id/statistics-table"


def item(identifier, title=None):
    return {"id": identifier, "title": title or f"Judul {identifier}", "url": URL}


class SearchAdapter:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def search(self, family, keyword, page=1):
        self.calls.append((family, keyword, page))
        result = self.results[family]
        if isinstance(result, Exception):
            raise result
        return result


def test_searches_all_catalogs_in_fixed_order_despite_partial_failure():
    adapter = SearchAdapter(
        {
            "simdasi": {"status": "empty", "items": [], "has_more": False},
            "dynamic": {"status": "ok", "items": [item("t1")], "has_more": False},
            "publication": TimeoutError(),
        }
    )

    result = asyncio.run(search_catalogs(adapter, "penduduk"))

    assert list(result) == ["simdasi", "dynamic", "publication"]
    assert [result[x]["status"] for x in result] == ["empty", "ok", "error"]
    assert len(adapter.calls) == 3


def test_adapter_rejects_malformed_fixture_and_limits_remote_page():
    malformed = BPSAdapter({"dynamic": {"items": "wrong"}}, app_env="test")
    fixture = BPSAdapter(
        {"dynamic": {"items": [item(str(x)) for x in range(7)], "has_more": True}},
        app_env="test",
    )

    bad = malformed.search("dynamic", "x")
    result = fixture.search("dynamic", "x")

    assert bad == {"error": {"code": "bps_schema_error"}}
    assert len(result["items"]) == 3
    assert result["has_more"] is True


def test_live_simdasi_uses_interoperability_service_and_parses_official_envelope():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={
            "status": "OK",
            "data": [{"page": 1}, {"data": [{
                "id_tabel": "table-1",
                "judul": "Jumlah Penduduk Kabupaten Padang Pariaman",
                "subject": "Kependudukan",
                "ketersediaan_tahun": [2024, 2023],
            }]}],
        })

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await BPSAdapter(api_key="secret", client=client).search("simdasi", "penduduk", 1)

    result = asyncio.run(run())

    assert "/interoperabilitas/datasource/simdasi/id/23/wilayah/1306000/key/secret" in seen["url"]
    assert "domain=" not in seen["url"]
    assert result["items"][0]["id"] == "table-1"
    assert result["items"][0]["periods"] == ["2024", "2023"]


def test_numbers_stably_across_pages_deduplicates_and_caps_frame_at_54():
    frame = new_frame("penduduk")
    page1 = {family: {"status": "ok", "items": [item(f"{family}{x}") for x in range(1, 4)], "has_more": True} for family in ("simdasi", "dynamic", "publication")}
    page2 = {family: {"status": "ok", "items": [item(f"{family}3"), item(f"{family}4"), item(f"{family}5"), item(f"{family}6")], "has_more": False} for family in ("simdasi", "dynamic", "publication")}

    add_page(frame, page1, 1)
    groups = add_page(frame, page2, 2)
    original = resolve_candidate(frame, "S1")

    assert [c.code for c in groups[0]["items"]] == ["S4", "S5", "S6"]
    assert original.source_identifier == "simdasi1"
    assert len(frame.candidates) == 18


def test_sanitizes_title_and_resolves_only_code_or_exact_unique_title():
    frame = new_frame("penduduk")
    add_page(frame, {"simdasi": {"items": [item("1", "Penduduk Umur 15<sup>+</sup> Tahun<script>alert(1)</script>"), item("2", "Judul Sama"), item("3", "Judul Sama")] }}, 1)

    safe = resolve_candidate(frame, "S1")

    assert safe.title == "Penduduk Umur 15+ Tahun"
    assert resolve_candidate(frame, " penduduk umur 15+ TAHUN ") is safe
    assert resolve_candidate(frame, "Judul Sama") is None
    assert resolve_candidate(frame, "S99") is None


def test_singleton_does_not_auto_select_and_invalid_or_stale_selection_never_fetches():
    frame = new_frame("penduduk")
    add_page(frame, {"simdasi": {"items": [item("1")] }}, 1)
    calls = []

    no_choice = select_candidate(frame, None, lambda candidate: calls.append(candidate))
    invalid = select_candidate(frame, "S99", lambda candidate: calls.append(candidate))
    stale = select_candidate(None, "S1", lambda candidate: calls.append(candidate))

    assert no_choice["error"]["code"] == "selection_required"
    assert invalid["error"]["code"] == "candidate_not_found"
    assert stale["error"]["code"] == "candidate_not_found"
    assert calls == []


def test_valid_explicit_selection_invokes_handler_once():
    frame = new_frame("penduduk")
    add_page(frame, {"dynamic": {"items": [item("42", "Jumlah Penduduk")] }}, 1)
    calls = []

    result = select_candidate(frame, "T1", lambda candidate: calls.append(candidate.code) or "periods")

    assert result == "periods"
    assert calls == ["T1"]


def test_rejects_page_after_stable_map_limit():
    frame = new_frame("penduduk")

    result = add_page(frame, {}, 7)

    assert result == {"error": {"code": "invalid_page"}}
    assert frame.candidates == {}
