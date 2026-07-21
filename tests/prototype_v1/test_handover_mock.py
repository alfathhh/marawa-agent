import pytest

from prototype_v1.handover import (
    GUESTBOOK_URL,
    HandoverAction,
    guestbook_url_allowed,
    mock_handover,
)


def test_offer_admin_is_explicitly_mock_and_offers_two_next_actions():
    result = mock_handover(HandoverAction.OFFER_ADMIN)

    assert result == {
        "status": "offered",
        "is_mock": True,
        "message": "Prototype ini belum tersambung ke petugas.",
        "actions": ["simulate_unavailable", "guestbook"],
    }


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        (HandoverAction.SIMULATE_UNAVAILABLE, "admin_unavailable"),
        (HandoverAction.DECLINE_WAIT, "guestbook_offered"),
    ],
)
def test_unavailable_paths_show_exact_official_guestbook(action, expected_status):
    result = mock_handover(action)

    assert result["status"] == expected_status
    assert result["is_mock"] is True
    assert result["guestbook_url"] == "https://s.bps.go.id/tamu1306"
    assert "petugas" in result["message"]


def test_guestbook_action_returns_exact_url_without_claiming_live_handover():
    result = mock_handover("guestbook")

    assert result["status"] == "guestbook_offered"
    assert result["guestbook_url"] == GUESTBOOK_URL == "https://s.bps.go.id/tamu1306"
    assert result["is_mock"] is True


def test_guestbook_allowlist_accepts_only_exact_https_bps_url():
    assert guestbook_url_allowed(GUESTBOOK_URL)
    for url in (
        "http://s.bps.go.id/tamu1306",
        "https://s.bps.go.id/tamu1306/",
        "https://example.com/tamu1306",
        "https://s.bps.go.id/tamu1306?next=evil",
        "https://s.bps.go.id/tamu1306.evil.example",
    ):
        assert not guestbook_url_allowed(url)


def test_unknown_action_is_stable_error_and_never_claims_admin_connection():
    result = mock_handover("connect_real_admin")

    assert result == {"error": {"code": "invalid_handover_action"}}
    assert "connected" not in str(result).lower()
