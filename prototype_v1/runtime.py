from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .catalog_service import add_page, new_frame, offer_periods, resolve_candidate, search_catalogs


class FixtureRuntime:
    """Small fixture-only vertical service; the HTTP controller may wrap it later."""

    def __init__(self, adapter):
        self.adapter = adapter
        self.frame = None
        self.candidate = None
        self.current_row = None

    async def search(self, query):
        self.frame = new_frame(query)
        results = await search_catalogs(self.adapter, query)
        groups = add_page(self.frame, results, 1)
        shaped = [{**group, "items": [{"code": item.code, "title": item.title, "url": item.url} for item in group["items"]]} for group in groups]
        unavailable = any(group["status"] == "error" for group in shaped)
        return {
            "text": "Sebagian sumber tidak tersedia; hasil yang ada tetap ditampilkan." if unavailable else "Saya menemukan beberapa sumber resmi. Pilih salah satu kode berikut, Kak.",
            "groups": shaped,
            "sources": [{"family": group["source"], "status": group["status"]} for group in shaped],
            "provenance": [],
        }

    async def select(self, code):
        self.candidate = resolve_candidate(self.frame, code)
        if self.candidate is None:
            return {"error": {"code": "candidate_not_found"}}
        periods = [{"value": value, "upstream_id": value, "label": value} for value in self.candidate.periods]
        offered = offer_periods(self.frame, self.candidate, periods)
        if "error" in offered:
            return offered
        return {
            "text": f"Sumber {code} tersedia untuk periode berikut. Pilih periodenya sebelum saya mengambil data:",
            "actions": [{"id": f"act_{x.value}", "label": x.label, "value": x.value, "kind": "period"} for x in offered["items"]],
            "sources": [{"family": self.candidate.source_family, "status": "ok"}],
            "provenance": [{"kind": "catalog", "title": self.candidate.title, "source_type": "Web API BPS - SIMDASI", "url": self.candidate.url}],
        }

    def _row(self, period):
        payload = (self.adapter.fixture or {}).get("data", {}).get(self.candidate.source_identifier, {}).get(period)
        if not isinstance(payload, dict) or not isinstance(payload.get("value"), str):
            return None
        value = Decimal(payload["value"])
        display = f"{value:,.0f}".replace(",", ".")
        return {"row_ref": f"row_penduduk_{period}", "value_decimal": payload["value"], "display_value": display, "unit": "jiwa", "period": period, "coverage": "Kabupaten Padang Pariaman", "indicator": "Jumlah Penduduk", "indicator_id": self.candidate.source_identifier, "coverage_code": "1306", "source_title": self.candidate.title, "source_type": "Web API BPS - SIMDASI", "source_url": self.candidate.url, "provenance": "verified", "answerable": True, "metadata_complete": True, "metadata_missing": []}

    async def fetch(self, period):
        row = self._row(period)
        if row is None:
            return {"error": {"code": "data_not_found"}}
        self.current_row = row
        return {"text": f"{row['indicator']} {row['coverage']} pada {period}: {row['display_value']} {row['unit']}.", "actions": [], "sources": [{"family": self.candidate.source_family, "status": "ok"}], "provenance": [{"kind": "verified_row", **{key: row[key] for key in ("row_ref", "display_value", "unit", "period", "coverage", "indicator")}, "title": row["source_title"], "source_type": row["source_type"], "url": row["source_url"]}]}

    async def compare(self, period):
        start, end = self._row(period), self.current_row
        if start is None or end is None:
            return {"error": {"code": "row_not_found"}}
        difference = Decimal(end["value_decimal"]) - Decimal(start["value_decimal"])
        percent = (difference / Decimal(start["value_decimal"]) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formatted_difference = f"{difference:,.0f}".replace(",", ".")
        formatted_percent = format(percent, "f").replace(".", ",")
        derived = {"kind": "derived", "start_row_ref": start["row_ref"], "end_row_ref": end["row_ref"], "difference": formatted_difference, "percent_change": formatted_percent, "direction": "naik" if difference > 0 else "turun" if difference < 0 else "tetap", "unit": end["unit"], "title": end["source_title"], "url": end["source_url"]}
        return {"text": f"{end['indicator']} {end['coverage']} {derived['direction']} dari {start['display_value']} {start['unit']} pada {period} menjadi {end['display_value']} {end['unit']} pada {end['period']}. Perubahan = {formatted_percent}%.", "actions": [], "sources": [{"family": self.candidate.source_family, "status": "ok"}], "provenance": [derived]}

    async def define(self, query):
        result = self.adapter.glossary(query)
        if hasattr(result, "__await__"):
            result = await result
        if "error" in result:
            return {"error": result["error"], "text": "Glosarium BPS sedang tidak tersedia. Saya tidak akan membuat definisi dari ingatan model."}
        return result

    @staticmethod
    def agent_fallback():
        return {"error": {"code": "agent_unavailable"}, "text": "Model tidak tersedia dan petugas belum terhubung. Pilih handover mock atau Buku Tamu.", "actions": ["handover", "guestbook"]}
