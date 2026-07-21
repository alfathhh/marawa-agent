import asyncio

from prototype_v1.bps_adapter import BPSAdapter
from prototype_v1.runtime import FixtureRuntime


FIXTURE = {
    "simdasi": {"items": [{"id": "s-pop", "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan", "url": "https://padangpariamankab.bps.go.id/id/statistics-table", "periods": ["2024", "2023"]}]},
    "dynamic": {"items": [{"id": "t-pop", "title": "Jumlah Penduduk Menurut Kecamatan", "url": "https://padangpariamankab.bps.go.id/id/statistics-table"}]},
    "publication": {"items": [{"id": "p-2025", "title": "Kabupaten Padang Pariaman Dalam Angka 2025", "url": "https://padangpariamankab.bps.go.id/id/publication"}]},
    "data": {
        "s-pop": {
            "2024": {"value": "434514"},
            "2023": {"value": "430000"},
        }
    },
}


def test_fixture_running_example_search_selection_period_data_compare():
    runtime = FixtureRuntime(BPSAdapter(FIXTURE, app_env="test"))

    search = asyncio.run(runtime.search("jumlah penduduk"))
    periods = asyncio.run(runtime.select("S1"))
    data = asyncio.run(runtime.fetch("2024"))
    comparison = asyncio.run(runtime.compare("2023"))

    assert [item["code"] for group in search["groups"] for item in group["items"]] == ["S1", "T1", "P1"]
    assert periods["actions"] == [{"id": "act_2024", "label": "2024", "value": "2024", "kind": "period"}, {"id": "act_2023", "label": "2023", "value": "2023", "kind": "period"}]
    assert data["provenance"][0]["display_value"] == "434.514"
    assert comparison["provenance"][0] == {"kind": "derived", "start_row_ref": "row_penduduk_2023", "end_row_ref": "row_penduduk_2024", "difference": "4.514", "percent_change": "1,05", "direction": "naik", "unit": "jiwa", "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan", "url": "https://padangpariamankab.bps.go.id/id/statistics-table"}
    assert "1,05%" in comparison["text"]


def test_fixture_runtime_rejects_development_adapter():
    runtime = FixtureRuntime(BPSAdapter(FIXTURE, app_env="development"))

    result = asyncio.run(runtime.search("penduduk"))

    assert all(group["status"] == "error" for group in result["groups"])
    assert not any(group["items"] for group in result["groups"])
