from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8") if isinstance(password, str) else b""
    if not 10 <= len(encoded) <= 72:
        raise ValueError("password must be 10-72 UTF-8 bytes")
    salt = os.urandom(16)
    digest = hashlib.scrypt(encoded, salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.urlsafe_b64encode(salt + digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(stored.removeprefix("scrypt$"))
        expected = raw[16:]
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=raw[:16], n=2**14, r=8, p=1
        )
        return stored.startswith("scrypt$") and hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_session(
    uid: int, role: str, secret: str, *, now: int | None = None, ttl: int = 43_200
):
    now = int(time.time()) if now is None else now
    csrf = _b64(os.urandom(18))
    payload = json.dumps(
        {"uid": uid, "role": role, "csrf": csrf, "exp": now + ttl},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    encoded = _b64(payload)
    signature = _b64(hmac.digest(secret.encode(), encoded.encode(), "sha256"))
    return encoded + "." + signature, csrf


def verify_request(
    token: str, csrf: str | None, method: str, secret: str, *, now: int | None = None
):
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.digest(secret.encode(), encoded.encode(), "sha256"))
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_decode(encoded))
        now = int(time.time()) if now is None else now
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < now:
            return None
        if method.upper() in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        } and not hmac.compare_digest(str(csrf or ""), str(payload.get("csrf", ""))):
            return None
        if payload.get("role") not in {"petugas", "superadmin"}:
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def mask_phone(phone: str) -> str:
    return (
        "*" * max(0, len(phone) - 4) + phone[-4:]
        if len(phone) > 4
        else "*" * len(phone)
    )
