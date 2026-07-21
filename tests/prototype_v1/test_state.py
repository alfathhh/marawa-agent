from dataclasses import replace
from datetime import UTC, datetime

from prototype_v1.models import Candidate, SearchFrame, SessionState
from prototype_v1.state import cancel_topic_switch, confirm_topic_switch, request_topic_switch


def make_frame():
    return SearchFrame(
        "search_old",
        "data penduduk",
        "data penduduk",
        candidates={
            "S1": Candidate("S1", "simdasi", "old", "Penduduk", "https://bps.go.id")
        },
        verified_rows={"row_old": {"value": "1"}},
    )


def make_session():
    now = datetime.now(UTC)
    return SessionState("pv1_x", "boot_x", now, now, frame=make_frame())


def test_new_topic_waits_for_confirmation_without_mutating_frame():
    session = make_session()
    original = session.frame

    request_topic_switch(session, "data kemiskinan")

    assert session.pending_topic == "data kemiskinan"
    assert session.frame is original
    assert session.frame.candidates["S1"].source_identifier == "old"


def test_confirm_discards_old_frame_and_returns_pending_query():
    session = make_session()
    request_topic_switch(session, "data kemiskinan")

    query = confirm_topic_switch(session)

    assert query == "data kemiskinan"
    assert session.pending_topic is None
    assert session.frame is None


def test_cancel_preserves_entire_old_frame_and_clears_pending_topic():
    session = make_session()
    original = replace(session.frame)
    request_topic_switch(session, "data kemiskinan")

    cancel_topic_switch(session)

    assert session.pending_topic is None
    assert session.frame == original


def test_follow_up_keeps_active_frame_without_catalog_reset():
    session = make_session()

    pending = request_topic_switch(session, "kalau tahun sebelumnya?", is_follow_up=True)

    assert pending is False
    assert session.pending_topic is None
    assert session.frame.search_id == "search_old"


def test_stale_candidate_code_is_rejected_without_fetch():
    calls = []
    session = make_session()

    result = session.frame.resolve_candidate("S99", lambda candidate: calls.append(candidate))

    assert result == {"error": {"code": "candidate_not_found"}}
    assert calls == []
