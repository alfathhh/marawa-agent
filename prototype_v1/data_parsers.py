from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .guardrails import DOMAIN, official_url, sanitize


_FIELDS = {
    "title": "source_title", "indicator": "indicator", "unit": "unit", "period": "period",
    "coverage": "coverage", "value": "value_decimal", "source_url": "source_url",
}


def _error(code, missing=None):
    error = {"code": code}
    if missing is not None:
        error["details"] = {"missing": sorted(missing)}
    return {"error": error}


def _decimal(value):
    if not isinstance(value, str) or not value or "," in value:
        raise InvalidOperation
    number = Decimal(value)
    if not number.is_finite():
        raise InvalidOperation
    return number


def _display(number):
    integer, dot, fraction = format(number, "f").partition(".")
    sign = "-" if integer.startswith("-") else ""
    integer = integer.removeprefix("-")
    grouped = f"{int(integer):,}".replace(",", ".")
    return sign + grouped + ("," + fraction if dot else "")


def _missing(payload, include_value=True, include_coverage=True):
    fields = _FIELDS if include_value else {k: v for k, v in _FIELDS.items() if k != "value"}
    if not include_coverage:
        fields = {k: v for k, v in fields.items() if k != "coverage"}
    return [output for key, output in fields.items() if not isinstance(payload.get(key), str) or not payload[key].strip()]


def _row(payload, value, coverage=None, coverage_code=None, source_type="SIMDASI", family="simdasi"):
    return {
        "value_decimal": value, "display_value": _display(value), "unit": sanitize(payload["unit"]),
        "period": sanitize(payload["period"]), "coverage": sanitize(coverage or payload["coverage"]),
        "coverage_code": coverage_code or payload["coverage_code"], "indicator": sanitize(payload["indicator"]),
        "source_title": sanitize(payload["title"]), "source_type": source_type,
        "source_url": payload["source_url"], "source_family": family, "answerable": True,
        "metadata_complete": True, "metadata_missing": [],
    }


def parse_simdasi(payload):
    if not isinstance(payload, dict) or payload.get("source_family") == "publication":
        return _error("bps_schema_error")
    missing = _missing(payload)
    if missing:
        return _error("metadata_incomplete", missing)
    if not official_url(payload["source_url"]):
        return _error("metadata_incomplete", ["source_url"])
    if payload.get("coverage_code") != DOMAIN:
        return _error("scope_mismatch")
    if payload.get("rows") == []:
        return _error("data_not_found")
    try:
        value = _decimal(payload["value"])
    except (InvalidOperation, ValueError):
        return _error("bps_schema_error")
    return {"rows": [_row(payload, value)]}


def parse_dynamic(payload):
    if not isinstance(payload, dict):
        return _error("bps_schema_error")
    missing = _missing(payload, include_value=False, include_coverage=False)
    if missing:
        return _error("metadata_incomplete", missing)
    if not official_url(payload["source_url"]):
        return _error("metadata_incomplete", ["source_url"])
    try:
        dimensions = {str(item["id"]): {str(k): v for k, v in item["values"].items()} for item in payload["dimensions"]}
        order = [str(item) for item in payload.get("dimension_order", dimensions)]
        if set(order) != set(dimensions):
            raise KeyError
        content = payload["datacontent"]
        entries = content if isinstance(content, list) else [
            {"dimensions": dict(zip(order, key.split("|"))), "value": value} for key, value in content.items()
        ]
        rows = []
        for entry in entries:
            members = {str(k): str(v) for k, v in entry["dimensions"].items()}
            if set(members) != set(order) or any(members[key] not in dimensions[key] for key in order):
                raise KeyError
            coverage_key = next(key for key in order if key.casefold() in {"wilayah", "domain", "coverage"})
            if members[coverage_key] != DOMAIN:
                continue
            rows.append(_row(payload, _decimal(entry["value"]), dimensions[coverage_key][DOMAIN], DOMAIN, "Tabel Dinamis", "dynamic"))
    except (KeyError, TypeError, AttributeError, InvalidOperation, ValueError):
        return _error("bps_schema_error")
    return {"rows": rows} if rows else _error("data_not_found")
