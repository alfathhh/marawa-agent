async def deliver_batch(
    store, evolution, claim_token: str, *, limit: int = 10, max_attempts: int = 8
):
    result = {"accepted": 0, "failed": 0}
    for row in store.claim_outbound(claim_token, limit=limit):
        response = await evolution.send_text(row["phone"], row["body"])
        if response.get("status") == "ACCEPTED":
            store.mark_accepted(row["id"], response.get("provider_message_id"))
            result["accepted"] += 1
            continue
        error = response.get("error")
        code = error.get("code") if isinstance(error, dict) else "evolution_unavailable"
        store.mark_failed(row["id"], claim_token, code, max_attempts=max_attempts)
        result["failed"] += 1
    return result
