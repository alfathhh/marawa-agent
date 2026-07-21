import asyncio

import httpx
import pytest

from prototype_v1.provider import GeminiNativeProvider


def run_provider(response, *, messages=None, tools=None):
    seen = {}

    def handler(request):
        seen["request"] = request
        return response

    client = httpx.AsyncClient(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        transport=httpx.MockTransport(handler),
    )
    provider = GeminiNativeProvider(client, "gemini-3.1-flash-lite", "test-key")
    result = asyncio.run(
        provider.request(messages or [{"role": "user", "content": "halo"}], tools or [])
    )
    asyncio.run(client.aclose())
    return result, seen["request"]


def test_gemini_native_sends_auth_and_normalizes_text():
    response = httpx.Response(
        200,
        json={"candidates": [{"content": {"parts": [{"text": "selesai"}]}}]},
    )

    result, request = run_provider(response)

    assert result == {"text": "selesai"}
    assert request.url.path.endswith("/models/gemini-3.1-flash-lite:generateContent")
    assert request.headers["x-goog-api-key"] == "test-key"


def test_gemini_native_normalizes_function_call():
    response = httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "kb_search",
                                    "args": {"query": "konsultasi"},
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )

    result, _ = run_provider(
        response,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "kb_search",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )

    assert result == {
        "tool_calls": [
            {"name": "kb_search", "arguments": {"query": "konsultasi"}}
        ]
    }


def test_gemini_native_hides_upstream_error_and_secret():
    response = httpx.Response(401, text="test-key raw upstream")

    with pytest.raises(RuntimeError, match="provider request failed") as error:
        run_provider(response)

    assert "test-key" not in str(error.value)
    assert error.value.__cause__ is None
