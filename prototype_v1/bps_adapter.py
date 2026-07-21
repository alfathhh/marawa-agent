from __future__ import annotations

import httpx

from .guardrails import sanitize, safe_error

BASE_URL = "https://webapi.bps.go.id/v1/api"
DOMAIN = "1306"
MODELS = {"simdasi": "simdasi", "dynamic": "var", "publication": "publication"}


class BPSAdapter:
    def __init__(self, fixture=None, app_env="development", *, api_key=None, client=None):
        self.fixture = fixture if app_env == "test" else None
        self.api_key = api_key
        self.client = client

    def search(self, family, keyword, page=1):
        if family not in MODELS or not isinstance(keyword, str) or not keyword.strip() or not isinstance(page, int) or page < 1:
            return safe_error("bps_schema_error")
        if self.fixture is not None:
            data = self.fixture.get(family)
            if isinstance(data, BaseException):
                return safe_error("bps_unavailable")
            return _parse_catalog(data)
        if not self.api_key or self.client is None:
            return safe_error("bps_unavailable")
        return self._request_catalog(family, keyword, page)

    async def _request_catalog(self, family, keyword, page):
        try:
            if family == "simdasi":
                response = await self.client.get(
                    f"{BASE_URL}/interoperabilitas/datasource/simdasi/id/23/wilayah/1306000/key/{self.api_key}",
                    headers={"User-Agent": "Marawa-Prototype/1 (development adapter)"},
                    timeout=httpx.Timeout(20, connect=5),
                )
                if response.status_code != 200:
                    return safe_error(classify_http(response.status_code))
                return _parse_simdasi_catalog(response.json(), keyword, page)
            response = await self.client.get(
                f"{BASE_URL}/list",
                params={"model": MODELS[family], "domain": DOMAIN, "keyword": keyword, "page": page, "key": self.api_key},
                headers={"User-Agent": "Marawa-Prototype/1 (development adapter)"},
                timeout=httpx.Timeout(20, connect=5),
            )
        except httpx.TimeoutException:
            return safe_error("bps_unavailable")
        if response.status_code != 200:
            return safe_error(classify_http(response.status_code))
        try:
            return _parse_catalog(response.json())
        except ValueError:
            return safe_error("bps_schema_error")

    def glossary(self, query):
        if self.fixture is not None:
            data = self.fixture.get("glossary")
            if not isinstance(data, dict) or "error" in data:
                return safe_error("glossary_unavailable")
            return _parse_glossary(data)
        if not self.api_key or self.client is None:
            return safe_error("glossary_unavailable")
        return self._request_glossary(query)

    async def _request_glossary(self, query):
        try:
            response = await self.client.get(f"{BASE_URL}/list", params={"model": "glosarium", "prefix": query, "page": 1, "perpage": 3, "key": self.api_key}, headers={"User-Agent": "Marawa-Prototype/1 (development adapter)"}, timeout=httpx.Timeout(20, connect=5))
        except httpx.TimeoutException:
            return safe_error("glossary_unavailable")
        if response.status_code != 200:
            return safe_error("glossary_unavailable")
        try:
            return _parse_glossary(response.json())
        except ValueError:
            return safe_error("glossary_schema_error")


def _parse_catalog(data):
    if not isinstance(data, dict):
        return safe_error("bps_schema_error")
    items = data.get("items", data.get("data"))
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        return safe_error("bps_schema_error")
    normalized = []
    for item in items[:3]:
        if not item.get("id") or not item.get("title") or not item.get("url"):
            return safe_error("bps_schema_error")
        normalized.append({**item, "id": str(item["id"]), "title": sanitize(item["title"])})
    total = data.get("total", len(items))
    return {"status": data.get("status") or ("ok" if normalized else "empty"), "items": normalized, "has_more": bool(data.get("has_more") or isinstance(total, int) and total > len(normalized) or len(items) > 3)}


def _parse_simdasi_catalog(payload, keyword, page):
    try:
        body = payload["data"][1]
        if str(payload.get("status", "")).casefold() != "ok" or not isinstance(body, dict):
            raise ValueError
        tables = body["data"]
        if not isinstance(tables, list):
            raise ValueError
        terms = set(sanitize(keyword).casefold().split())
        matches = []
        for table in tables:
            title = sanitize(table.get("judul", ""))
            table_id = table.get("id_tabel")
            if not title or table_id is None or (terms and not terms.intersection(title.casefold().split())):
                continue
            matches.append({
                "id": str(table_id),
                "title": title,
                "url": "https://padangpariamankab.bps.go.id/id/statistics-table",
                "subject": sanitize(table.get("subject", "")),
                "periods": [str(value) for value in table.get("ketersediaan_tahun", [])],
            })
        start = (page - 1) * 3
        items = matches[start : start + 3]
        return {"status": "ok" if items else "empty", "items": items, "has_more": len(matches) > start + 3}
    except (KeyError, TypeError, ValueError):
        return safe_error("bps_schema_error")


def _parse_glossary(data):
    items = data.get("items", data.get("data"))
    if isinstance(items, list) and len(items) == 2 and isinstance(items[1], list):
        items = items[1]
    if not isinstance(items, list):
        return safe_error("glossary_schema_error")
    try:
        rows = [item.get("_source", item) for item in items[:3]]
        return {"found": bool(rows), "items": [{"source_ref": f"glossary_{x['id']}", "concept": sanitize(x["konsep"]), "definition": sanitize(x["definisi"]), "indicator_title": sanitize(x.get("judulIndikator", "")), "unit": sanitize(x.get("satuan", "")), "source_content": sanitize(x.get("sumberKonten", "")), "source_url": "https://webapi.bps.go.id/documentation/#glosarium"} for x in rows]}
    except (AttributeError, KeyError, TypeError):
        return safe_error("glossary_schema_error")


def classify_http(status):
    if status == 401:
        return "bps_auth"
    if status == 429:
        return "bps_rate_limit"
    if status >= 500:
        return "bps_unavailable"
    return "bps_schema_error"


def parse_rows(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        return safe_error("bps_schema_error")
    return payload["rows"]


def parse_dynamic_dimensions(payload):
    try:
        dimensions = {str(x["id"]): x for x in payload["dimensions"]}
        return [(key, [dimensions[k]["values"][v] for k, v in zip(dimensions, key.split(":"))], value) for key, value in payload["datacontent"].items()]
    except (KeyError, TypeError, IndexError):
        return safe_error("bps_schema_error")
