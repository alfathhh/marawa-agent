import json
import time

from .templates import TEMPLATES

MAX_MODEL_REQUESTS = 6
MAX_TOOL_EXECUTIONS = 10
MAX_DUPLICATES = 2
DEADLINE_SECONDS = 120


def _fallback(code):
    return {
        "error": {"code": code},
        "text": TEMPLATES["LOOP_TRUNCATED"],
        "turn_status": "truncated",
    }


def run_agent_loop(model, registry, messages, *, context=None, clock=time.monotonic):
    started = clock()
    model_requests = 0
    tool_executions = 0
    duplicates = {}
    conversation = list(messages)
    while model_requests < MAX_MODEL_REQUESTS:
        if clock() - started >= DEADLINE_SECONDS:
            return _fallback("loop_budget_exceeded")
        try:
            response = model.request(conversation, registry.schemas())
        except Exception:
            return _fallback("agent_unavailable")
        model_requests += 1
        calls = response.get("tool_calls", []) if isinstance(response, dict) else []
        if not calls:
            text = response.get("text") if isinstance(response, dict) else None
            return {"text": text, "turn_status": "completed"} if isinstance(text, str) else _fallback("agent_unavailable")
        for call in calls:
            if tool_executions >= MAX_TOOL_EXECUTIONS:
                return _fallback("loop_budget_exceeded")
            name, args = call.get("name"), call.get("arguments")
            if not isinstance(name, str) or not isinstance(args, dict):
                return _fallback("invalid_arguments")
            canonical = json.dumps([name, args], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            duplicates[canonical] = duplicates.get(canonical, 0) + 1
            if duplicates[canonical] > MAX_DUPLICATES:
                return _fallback("duplicate_tool_call")
            result = registry.dispatch(name, args, context)
            tool_executions += 1
            if "error" in result:
                return _fallback(result["error"]["code"])
            conversation.append({"role": "tool", "name": name, "content": result})
    return _fallback("loop_budget_exceeded")
