from urllib.parse import urlparse


def _official(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and (
            parsed.hostname == "bps.go.id" or parsed.hostname.endswith(".bps.go.id")
        )
    except (AttributeError, ValueError):
        return False


def _render(result):
    if not isinstance(result, dict):
        return None
    text = result.get("text")
    sources = result.get("sources", [])
    if not isinstance(text, str) or not text.strip() or len(text) > 12_000:
        return None
    if not isinstance(sources, list):
        return None
    lines = []
    for source in sources:
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("title"), str)
            or not isinstance(source.get("url"), str)
            or not _official(source["url"])
        ):
            return None
        lines.append(f"• {source['title']} — {source['url']}")
    return text.strip() + ("\n\nSumber:\n" + "\n".join(lines) if lines else "")


async def process_inbound(store, runtime, row):
    try:
        reply = _render(await runtime(row["body"], row["phone"]))
    except Exception:
        return store.mark_inbound_failed(
            row["event_id"], row["claim_token"], "agent_unavailable"
        )
    if reply is None:
        return store.mark_inbound_failed(
            row["event_id"], row["claim_token"], "invalid_agent_output"
        )
    if not store.enqueue_outbound(row["phone"], reply, f"inbound:{row['event_id']}:1"):
        return store.mark_inbound_failed(
            row["event_id"], row["claim_token"], "outbox_unavailable"
        )
    store.mark_inbound_done(row["event_id"], row["claim_token"])
    return "DONE"
