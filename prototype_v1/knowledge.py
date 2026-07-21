from pathlib import Path
import re

import httpx
import yaml

from .guardrails import canonical, official_url, sanitize

_REQUIRED = {"source_key", "title", "source_url", "verified", "verified_by", "verified_at", "sections"}
_SECTION_KEYS = {"heading", "text", "aliases"}


def _validate_document(data):
    if not isinstance(data, dict) or set(data) != _REQUIRED or not isinstance(data["verified"], bool):
        raise ValueError("kb_schema_error")
    if not data["verified"]:
        return
    if not data["verified_by"] or not data["verified_at"] or not official_url(data["source_url"]):
        raise ValueError("kb_schema_error")
    if not isinstance(data["sections"], list):
        raise ValueError("kb_schema_error")
    for section in data["sections"]:
        if not isinstance(section, dict) or not set(section) <= _SECTION_KEYS or not {"heading", "text"} <= set(section):
            raise ValueError("kb_schema_error")


def _markdown_document(path):
    text = path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not match:
        raise ValueError("kb_schema_error")
    data = yaml.safe_load(match.group(1))
    body = match.group(2)
    sections = []
    heading = None
    lines = []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading:
                sections.append({"heading": heading, "text": "\n".join(lines).strip(), "aliases": []})
            heading, lines = line[3:].strip(), []
        elif heading:
            lines.append(line)
    if heading:
        sections.append({"heading": heading, "text": "\n".join(lines).strip(), "aliases": []})
    data["sections"] = sections
    return data


def load_documents(directory):
    docs = []
    for path in sorted(Path(directory).glob("*")):
        if path.suffix == ".yaml":
            data = yaml.safe_load(path.read_text())
        elif path.suffix == ".md":
            data = _markdown_document(path)
        else:
            continue
        _validate_document(data)
        if data["verified"]:
            docs.append(data)
    return docs


def search(docs, query, limit=4):
    tokens = set(canonical(query).split())
    ranked = []
    for doc in docs:
        for section in doc["sections"]:
            hay = canonical(" ".join([section["heading"], section["text"], *section.get("aliases", [])]))
            score = len(tokens & set(hay.split()))
            if score:
                ranked.append((score, {
                    "source_ref": f"kb_{doc['source_key']}_{canonical(section['heading']).replace(' ', '_')}",
                    "source_key": doc["source_key"], "title": sanitize(doc["title"]),
                    "heading": sanitize(section["heading"]), "text": sanitize(section["text"]),
                    "source_url": doc["source_url"], "verified_by": doc["verified_by"],
                    "verified_at": str(doc["verified_at"]),
                }))
    chunks = [item for _, item in sorted(ranked, key=lambda item: (-item[0], item[1]["source_ref"]))[:min(limit, 4)]]
    return {"found": bool(chunks), "chunks": chunks}


async def glossary_search(client, query, *, url):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
        return {"error": {"code": "invalid_query"}}
    response = None
    try:
        response = await client.get(url)
        if response.status_code == 429 or response.status_code >= 500:
            response = await client.get(url)
        if response.status_code != 200:
            return {"error": {"code": "glossary_unavailable"}}
        payload = response.json()
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError
        items = []
        for row in rows:
            if not isinstance(row, dict) or not {"glossary_id", "concept", "indicator_title", "definition", "unit"} <= set(row):
                raise ValueError
            items.append({"source_ref": f"glossary_{row['glossary_id']}", "concept": sanitize(row["concept"]), "indicator_title": sanitize(row["indicator_title"]), "definition": sanitize(row["definition"]), "unit": sanitize(row["unit"]), "source_content": "Glosarium Web API BPS", "source_url": "https://webapi.bps.go.id/documentation/#glosarium"})
        return {"found": bool(items), "items": items}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        code = "glossary_schema_error" if response is not None and response.status_code == 200 else "glossary_unavailable"
        return {"error": {"code": code}}


class TerritoryRegistry:
    def __init__(self, rows, verified):
        self.rows, self.verified = rows, verified

    def accepts(self, code, label):
        return self.verified and any(row.get("code") == code and row.get("label") == label and row.get("ancestor") == "1306" for row in self.rows)


def load_territories(path):
    data = yaml.safe_load(Path(path).read_text())
    return TerritoryRegistry(data.get("territories", []), data.get("verified") is True and bool(data.get("verified_by")) and bool(data.get("verified_at")))


def render_sources(items, conflict=False):
    blocks = [f"{x['title']} — {x.get('heading', x.get('context', ''))}\n{x.get('text', x.get('definition', ''))}\nSumber: {x.get('source_url') or x['title']}" for x in items]
    result = {"text": "\n\n".join(blocks), "actions": []}
    if conflict:
        result["text"] += "\n\nDua sumber terverifikasi ini memberi penjelasan berbeda. Saya tidak akan memilih salah satunya tanpa verifikasi petugas."
        result["actions"] = [{"id": "act_admin", "label": "Hubungi admin (simulasi)", "value": "offer_admin", "kind": "handover"}]
    return result


def no_match_response():
    return {"text": "Saya belum menemukan sumber resmi yang cukup untuk menjawab itu.", "actions": [{"id": "act_admin", "label": "Hubungi admin (simulasi)", "value": "offer_admin", "kind": "handover"}, {"id": "act_guestbook", "label": "Buku Tamu", "value": "https://s.bps.go.id/tamu1306", "kind": "link"}]}


def resolve_dimension(labels, query):
    exact = [x for x in labels if canonical(x) == canonical(query)]
    if len(exact) == 1:
        return exact[0]
    partial = [x for x in labels if canonical(query) in canonical(x)]
    return partial[0] if len(partial) == 1 else {"error": {"code": "ambiguous_dimension" if partial else "dimension_not_found", "details": {"candidates": partial}}}

__all__ = ["load_documents", "load_territories", "search", "glossary_search", "render_sources", "no_match_response", "resolve_dimension"]
