from datetime import UTC, datetime

from prototype_v1.followups import resolve_followup
from prototype_v1.models import Candidate, PeriodOption, SearchFrame, SessionState


def session(frame=True):
    now = datetime.now(UTC)
    active = SearchFrame(
        "search_1", "penduduk", "penduduk",
        candidates={"T1": Candidate("T1", "dynamic", "table-1", "Penduduk", "https://bps.go.id")},
        selected_code="T1",
        offered_periods=[PeriodOption("2024", "th-24", "2024"), PeriodOption("2023", "th-23", "2023")],
    ) if frame else None
    return SessionState("session", "boot", now, now, frame=active)


class Spy:
    def __init__(self):
        self.fetches = []
        self.searches = 0

    def fetch(self, candidate, period, dimensions):
        self.fetches.append((candidate.code, period.upstream_id, dimensions))
        return {"rows": ["ok"]}

    def search(self):
        self.searches += 1


def test_followup_uses_exact_offered_period_without_catalog_search():
    spy = Spy()

    result = resolve_followup(session(), "search_1", "2023", {}, {}, spy.fetch)

    assert result == {"rows": ["ok"]}
    assert spy.fetches == [("T1", "th-23", {})]
    assert spy.searches == 0


def test_ambiguous_dimension_returns_typed_clarification_without_fetch():
    spy = Spy()
    offered = {"sex": {"m": "Laki-laki", "f": "Perempuan"}}

    result = resolve_followup(session(), "search_1", "2024", offered, {}, spy.fetch)

    assert result == {"clarification": {"code": "dimension_required", "details": {"dimension": "sex", "options": ["f", "m"]}}}
    assert spy.fetches == []


def test_valid_dimension_fetches_exactly_once():
    spy = Spy()
    offered = {"sex": {"m": "Laki-laki", "f": "Perempuan"}}

    result = resolve_followup(session(), "search_1", "2024", offered, {"sex": "f"}, spy.fetch)

    assert result == {"rows": ["ok"]}
    assert spy.fetches == [("T1", "th-24", {"sex": "f"})]


def test_unoffered_period_and_dimension_do_not_fetch():
    spy = Spy()

    period = resolve_followup(session(), "search_1", "2022", {}, {}, spy.fetch)
    dimension = resolve_followup(session(), "search_1", "2024", {"sex": {"m": "Laki-laki"}}, {"sex": "x"}, spy.fetch)

    assert period["error"]["code"] == "period_not_available"
    assert dimension["error"]["code"] == "dimension_not_available"
    assert spy.fetches == []


def test_missing_and_stale_frames_return_typed_errors_without_fetch():
    spy = Spy()

    missing = resolve_followup(session(False), "search_1", "2024", {}, {}, spy.fetch)
    stale = resolve_followup(session(), "search_old", "2024", {}, {}, spy.fetch)

    assert missing == {"error": {"code": "followup_frame_missing"}}
    assert stale == {"error": {"code": "followup_frame_stale"}}
    assert spy.fetches == []
