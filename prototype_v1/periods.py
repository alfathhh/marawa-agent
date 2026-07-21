from __future__ import annotations

from .guardrails import sanitize, safe_error
from .models import PeriodOption

PAGE_SIZE = 20
MAX_PAGE = 10


def discover_periods(frame, candidate, adapter, page=1):
    if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= MAX_PAGE:
        return safe_error("invalid_page")
    if frame.candidates.get(candidate.code) is not candidate:
        return safe_error("candidate_not_found")
    if candidate.source_family == "publication":
        return safe_error("source_not_numeric")

    method = (
        adapter.list_simdasi_periods
        if candidate.source_family == "simdasi"
        else adapter.list_dynamic_periods
    )
    result = method(candidate.source_identifier)
    if not isinstance(result, dict):
        return safe_error("bps_schema_error")
    if "error" in result:
        return result
    raw_items = result.get("items")
    if not isinstance(raw_items, list):
        return safe_error("bps_schema_error")

    try:
        periods = [
            PeriodOption(str(item["value"]), str(item["upstream_id"]), sanitize(item["label"]))
            for item in raw_items
            if str(item["value"]) and str(item["upstream_id"]) and sanitize(item["label"])
        ]
    except (KeyError, TypeError):
        return safe_error("bps_schema_error")
    if not periods:
        return safe_error("periods_unavailable")

    start = (page - 1) * PAGE_SIZE
    items = periods[start : start + PAGE_SIZE]
    if not items:
        return safe_error("invalid_page")
    existing = {(item.value, item.upstream_id) for item in frame.offered_periods}
    frame.offered_periods.extend(
        item for item in items if (item.value, item.upstream_id) not in existing
    )
    frame.selected_code = candidate.code
    frame.selected_period = None
    return {
        "candidate_code": candidate.code,
        "page": page,
        "total": len(periods),
        "items": items,
        "has_more": page < MAX_PAGE and start + PAGE_SIZE < len(periods),
    }


def gate_period(frame, value):
    valid = [item.value for item in frame.offered_periods]
    if not isinstance(value, str) or value not in valid:
        return {"error": {"code": "period_not_available", "details": {"periods": valid}}}
    frame.selected_period = value
    return value
