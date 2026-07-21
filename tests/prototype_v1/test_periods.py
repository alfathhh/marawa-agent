from prototype_v1.models import Candidate
from prototype_v1.catalog_service import new_frame
from prototype_v1.periods import discover_periods, gate_period


class FakeAdapter:
    def __init__(self, simdasi=None, dynamic=None):
        self.simdasi = simdasi or []
        self.dynamic = dynamic or []
        self.calls = []

    def list_simdasi_periods(self, identifier):
        self.calls.append(("simdasi", identifier))
        return self.simdasi if isinstance(self.simdasi, dict) else {"items": self.simdasi}

    def list_dynamic_periods(self, identifier):
        self.calls.append(("dynamic", identifier))
        return self.dynamic if isinstance(self.dynamic, dict) else {"items": self.dynamic}


def candidate(code="S1", family="simdasi"):
    return Candidate(code, family, "id-1", "Title", "https://x.bps.go.id/table", periods=["2024", "2023"])


def offer(frame, item):
    frame.candidates[item.code] = item
    return item


def test_discovery_pages_simdasi_and_accumulates_without_selecting_latest():
    frame = new_frame("penduduk")
    adapter = FakeAdapter([{"value": str(year), "upstream_id": str(year), "label": str(year)} for year in range(2024, 2002, -1)])

    first = discover_periods(frame, offer(frame, candidate()), adapter, 1)
    second = discover_periods(frame, frame.candidates["S1"], adapter, 2)

    assert [x.value for x in first["items"]] == [str(year) for year in range(2024, 2004, -1)]
    assert [x.value for x in second["items"]] == ["2004", "2003"]
    assert len(frame.offered_periods) == 22
    assert frame.selected_code == "S1"
    assert frame.selected_period is None
    assert first["has_more"] is True
    assert second["has_more"] is False


def test_dynamic_discovery_uses_th_and_gate_rejects_unoffered_period():
    frame = new_frame("penduduk")
    t1 = offer(frame, candidate("T1", "dynamic"))
    adapter = FakeAdapter(dynamic=[{"value": "2024", "upstream_id": "th-2024", "label": "2024"}])

    result = discover_periods(frame, t1, adapter, 1)

    assert adapter.calls == [("dynamic", "id-1")]
    assert result["items"][0].upstream_id == "th-2024"
    assert gate_period(frame, "2022")["error"]["code"] == "period_not_available"
    assert frame.selected_period is None


def test_invalid_page_stale_candidate_and_adapter_error_block_without_state_change():
    frame = new_frame("penduduk")
    valid = offer(frame, candidate())
    adapter = FakeAdapter()

    assert discover_periods(frame, valid, adapter, 0)["error"]["code"] == "invalid_page"
    assert discover_periods(frame, candidate("S99"), adapter, 1)["error"]["code"] == "candidate_not_found"
    assert frame.offered_periods == []

    adapter.simdasi = {"error": {"code": "periods_unavailable"}}
    assert discover_periods(frame, valid, adapter, 1)["error"]["code"] == "periods_unavailable"
    assert frame.offered_periods == []


def test_gate_accepts_offered_period_and_does_not_fetch():
    frame = new_frame("penduduk")
    frame.offered_periods = []
    adapter = FakeAdapter([{"value": "2024", "upstream_id": "2024", "label": "2024"}])
    discover_periods(frame, offer(frame, candidate()), adapter, 1)

    assert gate_period(frame, "2024") == "2024"
    assert frame.selected_period == "2024"
    assert adapter.calls == [("simdasi", "id-1")]


def test_publication_has_no_periods():
    frame = new_frame("penduduk")
    assert discover_periods(frame, offer(frame, candidate("P1", "publication")), FakeAdapter(), 1)["error"]["code"] == "source_not_numeric"


def test_maximum_ten_pages():
    frame = new_frame("penduduk")
    assert discover_periods(frame, offer(frame, candidate()), FakeAdapter(), 11)["error"]["code"] == "invalid_page"
    assert gate_period(frame, "2024")["error"]["code"] == "period_not_available"
