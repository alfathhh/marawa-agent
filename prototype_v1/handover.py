from enum import StrEnum


GUESTBOOK_URL = "https://s.bps.go.id/tamu1306"
_MOCK_MESSAGE = "Prototype ini belum tersambung ke petugas."


class HandoverAction(StrEnum):
    OFFER_ADMIN = "offer_admin"
    SIMULATE_UNAVAILABLE = "simulate_unavailable"
    DECLINE_WAIT = "decline_wait"
    GUESTBOOK = "guestbook"


def guestbook_url_allowed(url: str) -> bool:
    return url == GUESTBOOK_URL


def mock_handover(action: str | HandoverAction) -> dict:
    try:
        action = HandoverAction(action)
    except (TypeError, ValueError):
        return {"error": {"code": "invalid_handover_action"}}

    if action is HandoverAction.OFFER_ADMIN:
        return {
            "status": "offered",
            "is_mock": True,
            "message": _MOCK_MESSAGE,
            "actions": [
                HandoverAction.SIMULATE_UNAVAILABLE.value,
                HandoverAction.GUESTBOOK.value,
            ],
        }

    return {
        "status": (
            "admin_unavailable"
            if action is HandoverAction.SIMULATE_UNAVAILABLE
            else "guestbook_offered"
        ),
        "is_mock": True,
        "message": _MOCK_MESSAGE,
        "guestbook_url": GUESTBOOK_URL,
    }
