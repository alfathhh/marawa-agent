from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

_TWO_PLACES = Decimal("0.01")
_CANONICAL_DECIMAL = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?\Z")


def format_id(value):
    value = Decimal(str(value))
    sign = "-" if value < 0 else ""
    whole, dot, fraction = format(abs(value), "f").partition(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return sign + ".".join(reversed(groups)) + (("," + fraction) if dot else "")


def _verified(row):
    return bool(
        isinstance(row, dict)
        and row.get("row_ref")
        and row.get("answerable") is True
        and row.get("metadata_complete") is True
        and not row.get("metadata_missing")
        and row.get("provenance") == "verified"
    )


def _decimal(row):
    raw = row.get("value_decimal")
    if not isinstance(raw, str) or not _CANONICAL_DECIMAL.fullmatch(raw):
        raise ValueError
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError from exc
    if not value.is_finite():
        raise ValueError
    return value


def _error(code, reason=None):
    error = {"code": code}
    if reason:
        error["details"] = {"reason": reason}
    return {"error": error}


def compare_rows(start, end):
    if not start or not end:
        return _error("row_not_found")
    if not _verified(start) or not _verified(end):
        return _error("rows_not_comparable", "unverified")
    for field, reason in (
        ("indicator_id", "indicator"),
        ("unit", "unit"),
        ("coverage_code", "coverage"),
    ):
        if not start.get(field) or start[field] != end.get(field):
            return _error("rows_not_comparable", reason)
    if not start.get("period") or start["period"] == end.get("period"):
        return _error("rows_not_comparable", "period")
    try:
        initial, final = _decimal(start), _decimal(end)
    except ValueError:
        return _error("rows_not_comparable", "invalid_value")
    if initial == 0:
        return _error("zero_baseline")

    difference = (final - initial).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    percent = ((final - initial) / initial * 100).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return {
        "start_row_ref": start["row_ref"],
        "end_row_ref": end["row_ref"],
        "difference_decimal": format(difference, "f"),
        "difference_display": format_id(difference),
        "percent_decimal": format(percent, "f"),
        "percent_display": format_id(percent),
        "direction": "naik" if difference > 0 else "turun" if difference < 0 else "tetap",
        "formula": f"({end['value_decimal']} - {start['value_decimal']}) / {start['value_decimal']} × 100",
        "provenance": {
            "kind": "derived",
            "source_refs": [start["row_ref"], end["row_ref"]],
        },
    }


def render_analysis(result, start, end):
    if "error" in result or result.get("provenance", {}).get("kind") != "derived":
        raise ValueError("renderer requires a successful derived result")
    return "\n".join(
        (
            f"{start['indicator']} — {start['coverage']}",
            f"Nilai awal ({start['period']}): {start['display_value']} {start['unit']}",
            f"Nilai akhir ({end['period']}): {end['display_value']} {end['unit']}",
            f"Rumus selisih: {end['value_decimal']} - {start['value_decimal']} = {result['difference_display']} {start['unit']}",
            f"Rumus persen: {result['formula']} = {result['percent_display']}%",
            f"Arah: {result['direction']}",
            f"Sumber awal [{start['row_ref']}]: {start['source_title']} ({start['source_type']}) — {start['source_url']}",
            f"Sumber akhir [{end['row_ref']}]: {end['source_title']} ({end['source_type']}) — {end['source_url']}",
            f"Provenance: derived dari verified rows {start['row_ref']} dan {end['row_ref']}.",
        )
    )
