import json

import pytest

from prototype_v1.provider import OpenAICompatibleProvider


class FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.chat = type("Chat", (), {"completions": FakeCompletions(response)})()


@pytest.mark.parametrize("provider_name", ["gemini", "9router"])
def test_openai_compatible_provider_uses_only_native_portable_parameters(provider_name):
    response = type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "selesai", "tool_calls": None})()})()]})()
    client = FakeClient(response)
    provider = OpenAICompatibleProvider(client, f"{provider_name}-model")

    assert provider.request([{"role": "user", "content": "halo"}], []) == {"text": "selesai"}
    assert client.chat.completions.kwargs == {
        "model": f"{provider_name}-model",
        "messages": [{"role": "user", "content": "halo"}],
        "tools": [],
        "temperature": 0,
        "parallel_tool_calls": False,
    }


def test_provider_normalizes_native_tool_calls_to_agent_loop_schema():
    function = type("Function", (), {"name": "kb_search", "arguments": json.dumps({"query": "konsultasi"})})()
    tool_call = type("ToolCall", (), {"function": function})()
    message = type("Message", (), {"content": None, "tool_calls": [tool_call]})()
    client = FakeClient(type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})())

    result = OpenAICompatibleProvider(client, "candidate").request([], [{"type": "function"}])

    assert result == {"tool_calls": [{"name": "kb_search", "arguments": {"query": "konsultasi"}}]}


@pytest.mark.parametrize("arguments", ["not json", "[]", "null"])
def test_provider_rejects_malformed_or_non_object_tool_arguments(arguments):
    function = type("Function", (), {"name": "kb_search", "arguments": arguments})()
    message = type("Message", (), {"content": None, "tool_calls": [type("ToolCall", (), {"function": function})()]})()
    client = FakeClient(type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})())

    with pytest.raises(ValueError, match="invalid provider tool arguments"):
        OpenAICompatibleProvider(client, "candidate").request([], [])


def test_provider_never_exposes_raw_upstream_error():
    class Broken:
        def create(self, **kwargs):
            raise RuntimeError("sk-live-secret upstream body")

    client = type("Client", (), {"chat": type("Chat", (), {"completions": Broken()})()})()

    with pytest.raises(RuntimeError, match="provider request failed") as error:
        OpenAICompatibleProvider(client, "candidate").request([], [])

    assert "secret" not in str(error.value)
    assert error.value.__cause__ is None


def test_provider_rejects_empty_or_invalid_response_shape():
    client = FakeClient(type("Response", (), {"choices": []})())

    with pytest.raises(RuntimeError, match="invalid provider response"):
        OpenAICompatibleProvider(client, "candidate").request([], [])


def test_provider_conformance_is_mock_only_not_a_production_candidate_gate():
    assert OpenAICompatibleProvider.conformance_scope == "mock-schema-only"
    assert OpenAICompatibleProvider.production_candidate_verified is False
