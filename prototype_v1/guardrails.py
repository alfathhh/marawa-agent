from __future__ import annotations
import html
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

DOMAIN = "1306"
PROVENANCE_TYPES = {
    "verified",
    "derived",
    "sourced_knowledge",
    "quoted_user",
    "structural",
}


@dataclass(frozen=True)
class Provenance:
    kind: str
    source_ref: str | None = None
    text: str | None = None

    def __post_init__(self):
        if self.kind not in PROVENANCE_TYPES:
            raise ValueError("invalid provenance kind")
        if self.kind == "sourced_knowledge" and not self.source_ref:
            raise ValueError("sourced knowledge requires source ref")


def canonical(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def sanitize(text):
    text = html.unescape(unicodedata.normalize("NFKC", str(text)))
    text = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return "".join(
        c for c in text if c in "\n\t" or unicodedata.category(c)[0] != "C"
    ).strip()


def official_url(url, *, guestbook=False):
    try:
        p = urlparse(url)
    except ValueError:
        return False
    valid = (
        p.scheme == "https"
        and (p.hostname == "bps.go.id" or (p.hostname or "").endswith(".bps.go.id"))
        and not p.username
        and not p.password
        and p.port in (None, 443)
    )
    return valid and (not guestbook or url == "https://s.bps.go.id/tamu1306")


def validate_metadata(row, territory=None):
    required = (
        "value_decimal",
        "display_value",
        "unit",
        "period",
        "coverage",
        "coverage_code",
        "indicator",
        "source_title",
        "source_type",
        "source_url",
    )
    missing = [x for x in required if not row.get(x)]
    try:
        Decimal(str(row.get("value_decimal", "")))
    except InvalidOperation:
        missing.append("value_decimal")
    if not official_url(row.get("source_url", "")):
        missing.append("source_url")
    if row.get("source_family") == "publication":
        missing.append("source_family")
    if row.get("coverage_code") != DOMAIN and not (
        territory and territory.accepts(row.get("coverage_code"), row.get("coverage"))
    ):
        missing.append("coverage")
    if (
        not row.get("answerable")
        or not row.get("metadata_complete")
        or row.get("metadata_missing")
    ):
        missing.append("metadata")
    return sorted(set(missing))


def gate_domain(args):
    if "domain" in args:
        return {"error": {"code": "scope_domain_not_allowed"}}
    return None


def prepare_tool_args(args, allowed):
    domain_error = gate_domain(args)
    if domain_error:
        return domain_error
    if set(args) - set(allowed):
        return {"error": {"code": "invalid_arguments"}}
    return {**args, "domain": DOMAIN}


def safe_error(code):
    return {"error": {"code": code}}
