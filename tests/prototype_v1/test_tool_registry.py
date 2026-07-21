from prototype_v1.tool_registry import ToolRegistry


def test_dispatch_injects_context_and_domain_after_strict_validation():
    calls = []
    registry = ToolRegistry()
    registry.register(
        "search",
        lambda **kwargs: calls.append(kwargs) or {"ok": True},
        {"keyword": str, "page": int},
        inject_domain=True,
    )

    result = registry.dispatch("search", {"keyword": "penduduk", "page": 1}, {"session": "s1"})

    assert result == {"ok": True}
    assert calls == [{"keyword": "penduduk", "page": 1, "context": {"session": "s1"}, "domain": "1306"}]


def test_invalid_calls_never_execute_handler():
    calls = []
    registry = ToolRegistry()
    registry.register("search", lambda **kwargs: calls.append(kwargs), {"keyword": str, "page": int})

    results = [
        registry.dispatch("missing", {}),
        registry.dispatch("search", {"keyword": "x"}),
        registry.dispatch("search", {"keyword": "x", "page": 1, "extra": True}),
        registry.dispatch("search", {"keyword": "x", "page": True}),
        registry.dispatch("search", {"keyword": "x", "page": 1, "domain": "1306"}),
    ]

    assert [item["error"]["code"] for item in results] == [
        "unknown_tool",
        "invalid_arguments",
        "invalid_arguments",
        "invalid_arguments",
        "invalid_arguments",
    ]
    assert calls == []


def test_handler_exception_becomes_stable_error():
    registry = ToolRegistry()
    registry.register("broken", lambda: 1 / 0, {})

    assert registry.dispatch("broken", {}) == {"error": {"code": "internal_error"}}


def test_registry_exposes_strict_closed_model_schema():
    registry = ToolRegistry()
    registry.register("search", lambda **_: {}, {"keyword": str, "page": int})

    schema = registry.schemas()[0]

    assert schema["function"]["strict"] is True
    assert schema["function"]["parameters"]["additionalProperties"] is False
    assert schema["function"]["parameters"]["required"] == ["keyword", "page"]
    assert "domain" not in schema["function"]["parameters"]["properties"]


def test_domain_constraints_are_rejected_before_handler():
    calls = []
    registry = ToolRegistry()
    registry.register("search", lambda **kwargs: calls.append(kwargs), {"page": {"type": "integer", "minimum": 1, "maximum": 6}})

    result = registry.dispatch("search", {"page": 7})

    assert result == {"error": {"code": "invalid_arguments"}}
    assert calls == []


def test_dispatch_order_is_serial():
    events = []
    registry = ToolRegistry()
    registry.register("first", lambda: events.append("first") or {}, {})
    registry.register("second", lambda: events.append("second") or {}, {})

    registry.dispatch_many([("first", {}), ("second", {})])

    assert events == ["first", "second"]
