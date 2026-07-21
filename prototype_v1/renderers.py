from __future__ import annotations

from .guardrails import official_url, sanitize


def render_data(rows):
    blocks = []
    for row in rows[:10]:
        blocks.append(
            f"Indikator: {row['indicator']}\nNilai: {row['display_value']}\nSatuan: {row['unit']}\n"
            f"Periode: {row['period']}\nCakupan: {row['coverage']} ({row['coverage_code']})\n"
            f"Judul sumber: {row['source_title']}\nJenis sumber: {row['source_type']}\n"
            f"URL sumber: {row['source_url']}"
        )
    total = len(rows)
    suffix = f"Total data: {total}."
    if total > 10:
        suffix += " Ditampilkan 10; rincian lainnya tersedia."
    return "\n\n".join(blocks) + "\n" + suffix


def render_publication(candidate, frame=None):
    if candidate.source_family != "publication":
        return {"error": {"code": "source_not_publication"}}
    if not official_url(candidate.url):
        return {"error": {"code": "invalid_source_url"}}
    abstract = sanitize(candidate.abstract) if candidate.abstract else "Abstraksi tidak tersedia pada metadata BPS."
    return {
        "text": f"Judul: {sanitize(candidate.title)}\nAbstraksi: {abstract}\nBaca/unduh: {candidate.url}",
        "provenance": {"kind": "structural", "source_url": candidate.url},
    }
