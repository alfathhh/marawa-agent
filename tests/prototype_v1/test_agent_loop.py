from prototype_v1.agent_loop import run_agent_loop
from prototype_v1.tool_registry import ToolRegistry


class ScriptedModel:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.requests = 0

    def request(self, messages, tools):
        self.requests += 1
        return next(self.replies)


def call(name="ping", arguments=None):
    return {"name": name, "arguments": arguments or {}}


def test_loop_executes_tools_serially_then_returns_model_text():
    events = []
    registry = ToolRegistry()
    registry.register("ping", lambda: events.append("tool") or {"pong": True}, {})
    model = ScriptedModel([{"tool_calls": [call()]}, {"text": "selesai"}])

    result = run_agent_loop(model, registry, [], clock=lambda: 0)

    assert result == {"text": "selesai", "turn_status": "completed"}
    assert events == ["tool"]
    assert model.requests == 2


def test_third_canonical_duplicate_is_blocked_before_execution():
    executions = []
    registry = ToolRegistry()
    registry.register("ping", lambda: executions.append(1) or {}, {})
    model = ScriptedModel([{"tool_calls": [call()]}] * 3)

    result = run_agent_loop(model, registry, [], clock=lambda: 0)

    assert result["error"]["code"] == "duplicate_tool_call"
    assert result["turn_status"] == "truncated"
    assert len(executions) == 2


def test_model_request_budget_is_six():
    registry = ToolRegistry()
    registry.register("ping", lambda: {}, {})
    model = ScriptedModel([{"tool_calls": [call(arguments={"n": n})]} for n in range(6)])
    registry.register("ping", lambda **_: {}, {"n": int})

    result = run_agent_loop(model, registry, [], clock=lambda: 0)

    assert result["error"]["code"] == "loop_budget_exceeded"
    assert model.requests == 6


def test_tool_execution_budget_is_ten():
    executions = []
    registry = ToolRegistry()
    registry.register("ping", lambda **_: executions.append(1) or {}, {"n": int})
    model = ScriptedModel([{"tool_calls": [call(arguments={"n": n}) for n in range(11)]}])

    result = run_agent_loop(model, registry, [], clock=lambda: 0)

    assert result["error"]["code"] == "loop_budget_exceeded"
    assert len(executions) == 10


def test_deadline_is_120_seconds_and_returns_safe_typed_fallback():
    times = iter([0, 121])
    registry = ToolRegistry()
    model = ScriptedModel([{"text": "should not be reached"}])

    result = run_agent_loop(model, registry, [], clock=lambda: next(times))

    assert result == {
        "error": {"code": "loop_budget_exceeded"},
        "text": "Saya belum dapat menyelesaikan permintaan ini dalam batas proses yang aman.",
        "turn_status": "truncated",
    }
    assert model.requests == 0


def test_invalid_model_or_tool_failure_returns_typed_safe_fallback():
    registry = ToolRegistry()
    model = ScriptedModel([{"tool_calls": [call("unknown")] }])

    result = run_agent_loop(model, registry, [], clock=lambda: 0)

    assert result["error"]["code"] == "unknown_tool"
    assert "unknown" not in result["text"]
    assert result["turn_status"] == "truncated"
