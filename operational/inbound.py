from operational.bridge import process_inbound


async def process_batch(store, runtime, claim_token: str, *, limit: int = 10):
    result = {"done": 0, "failed": 0}
    for row in store.claim_inbound(claim_token, limit=limit):
        status = await process_inbound(store, runtime, row)
        result["done" if status == "DONE" else "failed"] += 1
    return result
