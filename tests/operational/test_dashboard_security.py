import time

from operational.dashboard_security import (
    hash_password,
    issue_session,
    mask_phone,
    verify_password,
    verify_request,
)


SECRET = "k" * 32


def test_password_hash_is_salted_and_verifiable():
    one = hash_password("password-ku")
    two = hash_password("password-ku")

    assert one != two
    assert verify_password("password-ku", one)
    assert not verify_password("salah", one)
    assert "password-ku" not in one


def test_signed_session_rejects_tampering_and_expiry():
    token, csrf = issue_session(7, "petugas", SECRET, now=100, ttl=60)

    assert verify_request(token, None, "GET", SECRET, now=120) == {
        "uid": 7,
        "role": "petugas",
        "csrf": csrf,
        "exp": 160,
        "version": 1,
    }
    assert verify_request(token + "x", None, "GET", SECRET, now=120) is None
    assert verify_request(token, None, "GET", SECRET, now=161) is None


def test_mutation_requires_exact_csrf():
    token, csrf = issue_session(7, "petugas", SECRET, now=int(time.time()))

    assert verify_request(token, None, "POST", SECRET) is None
    assert verify_request(token, "wrong", "POST", SECRET) is None
    assert verify_request(token, csrf, "POST", SECRET)["uid"] == 7


def test_phone_masking_preserves_only_last_four_digits():
    assert mask_phone("628123456789") == "********6789"
    assert mask_phone("123") == "***"


def test_invalid_password_boundaries_are_rejected():
    for password in ("short", "x" * 73):
        try:
            hash_password(password)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid password accepted")


def test_role_is_signed_not_caller_controlled():
    token, _ = issue_session(1, "petugas", SECRET)
    payload = verify_request(token, None, "GET", SECRET)
    assert payload["role"] == "petugas"
    assert payload["role"] != "superadmin"
