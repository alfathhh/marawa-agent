from __future__ import annotations


def _error(code, details=None):
    error = {"code": code}
    if details is not None:
        error["details"] = details
    return {"error": error}


def resolve_followup(session, search_id, period, offered_dimensions, dimensions, fetch):
    """Resolve against the active frame only; fetch is called once after all gates pass."""
    frame = session.frame
    if frame is None:
        return _error("followup_frame_missing")
    if frame.search_id != search_id:
        return _error("followup_frame_stale")

    offered = {item.value: item for item in frame.offered_periods}
    if period not in offered:
        return _error("period_not_available", {"periods": sorted(offered)})

    dimensions = dimensions or {}
    for name, options in (offered_dimensions or {}).items():
        if name not in dimensions:
            if len(options) > 1:
                return {"clarification": {"code": "dimension_required", "details": {"dimension": name, "options": sorted(options)}}}
            if len(options) == 1:
                dimensions[name] = next(iter(options))
        elif dimensions[name] not in options:
            return _error("dimension_not_available")
    for name in dimensions:
        if name not in offered_dimensions:
            return _error("dimension_not_available")

    candidate = frame.candidates.get(frame.selected_code)
    if candidate is None:
        return _error("followup_frame_stale")
    frame.selected_period = period
    return fetch(candidate, offered[period], dimensions)


# ponytail: dimension labels are intentionally not inferred; add typed parsing only with a contract.

__all__ = ["resolve_followup"]
