from __future__ import annotations

import asyncio
import inspect
import secrets

from .guardrails import canonical, official_url, sanitize
from .models import Candidate, PeriodOption, SearchFrame

FAMILIES = (
    ("simdasi", "S", "SIMDASI"),
    ("dynamic", "T", "Tabel Dinamis"),
    ("publication", "P", "Publikasi"),
)


async def search_catalogs(adapter, keyword, page=1):
    async def one(family):
        try:
            result = adapter.search(family, keyword, page)
            result = await result if inspect.isawaitable(result) else result
            items = result.get("items") if isinstance(result, dict) else None
            if "error" in result or not isinstance(items, list):
                raise ValueError
            return {
                "status": result.get("status") or ("ok" if items else "empty"),
                "items": items[:3],
                "has_more": bool(result.get("has_more") or len(items) > 3),
            }
        except Exception:
            return {"status": "error", "items": [], "has_more": False}

    values = await asyncio.gather(*(one(family) for family, _, _ in FAMILIES))
    return {family: value for (family, _, _), value in zip(FAMILIES, values)}


def new_frame(query):
    return SearchFrame("search_" + secrets.token_urlsafe(10), query, canonical(query))


def add_page(frame, results, page):
    if not 1 <= page <= 6:
        return {"error": {"code": "invalid_page"}}
    groups = []
    for family, prefix, label in FAMILIES:
        result = results.get(family, {"status": "error", "items": []})
        added = []
        known = {
            c.source_identifier
            for c in frame.candidates.values()
            if c.source_family == family
        }
        number = 1 + len(known)
        for item in result.get("items", []):
            ident = str(item.get("id", ""))
            if not ident or ident in known or not official_url(item.get("url", "")):
                continue
            code = f"{prefix}{number}"
            number += 1
            known.add(ident)
            candidate = Candidate(
                code,
                family,
                ident,
                sanitize(item.get("title", "")),
                item["url"],
                sanitize(item.get("subject", "")) or None,
                [str(x) for x in item.get("periods", [])],
                sanitize(item.get("abstract", "")) or None,
                page,
            )
            frame.candidates[code] = candidate
            added.append(candidate)
            if len(added) == 3:
                break
        groups.append(
            {
                "source": family,
                "label": label,
                "status": result.get("status", "ok"),
                "has_more": bool(result.get("has_more")),
                "items": added,
            }
        )
    frame.page = page
    return groups


def resolve_candidate(frame, value):
    if frame is None or not isinstance(value, str):
        return None
    code = value.strip().upper()
    if code in frame.candidates:
        return frame.candidates[code]
    matches = [
        c for c in frame.candidates.values() if canonical(c.title) == canonical(value)
    ]
    return matches[0] if len(matches) == 1 else None


def select_candidate(frame, value, handler):
    if value is None:
        return {"error": {"code": "selection_required"}}
    candidate = resolve_candidate(frame, value)
    if candidate is None:
        return {"error": {"code": "candidate_not_found"}}
    return handler(candidate)


def offer_periods(frame, candidate, periods, page=1):
    if candidate.source_family == "publication":
        return {"error": {"code": "source_not_numeric"}}
    if not 1 <= page <= 10:
        return {"error": {"code": "invalid_page"}}
    items = [
        PeriodOption(
            str(x.get("value")), str(x.get("upstream_id")), sanitize(x.get("label"))
        )
        for x in periods[(page - 1) * 20 : page * 20]
    ]
    existing = {x.value for x in frame.offered_periods}
    frame.offered_periods.extend(x for x in items if x.value not in existing)
    frame.selected_code = candidate.code
    return {
        "candidate_code": candidate.code,
        "page": page,
        "items": items,
        "has_more": page * 20 < len(periods),
        "total": len(periods),
    }


def select_period(frame, value):
    if value not in {x.value for x in frame.offered_periods}:
        return {
            "error": {
                "code": "period_not_available",
                "details": {"periods": [x.value for x in frame.offered_periods]},
            }
        }
    frame.selected_period = value
    return value
