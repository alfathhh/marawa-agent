import asyncio

import httpx

from prototype_v1.bps_adapter import BPSAdapter
from prototype_v1.runtime import FixtureRuntime


def test_partial_catalog_failures_are_visible_without_fabricated_results():
    fixture = {
        "simdasi": {"items": []},
        "dynamic": {"items": "malformed"},
        "publication": TimeoutError(),
    }
    runtime = FixtureRuntime(BPSAdapter(fixture, app_env="test"))

    result = asyncio.run(runtime.search("penduduk"))

    assert [group["status"] for group in result["groups"]] == ["empty", "error", "error"]
    assert result["provenance"] == []
    assert "tidak tersedia" in result["text"].lower()


def test_glossary_failure_and_llm_exhaustion_return_honest_admin_fallback():
    runtime = FixtureRuntime(BPSAdapter({"glossary": {"error": "upstream"}}, app_env="test"))

    glossary = asyncio.run(runtime.define("penduduk"))
    fallback = runtime.agent_fallback()

    assert glossary == {"error": {"code": "glossary_unavailable"}, "text": "Glosarium BPS sedang tidak tersedia. Saya tidak akan membuat definisi dari ingatan model."}
    assert fallback["error"]["code"] == "agent_unavailable"
    assert fallback["actions"] == ["handover", "guestbook"]
    assert "petugas belum terhubung" in fallback["text"].lower()


def test_live_adapter_injects_domain_key_user_agent_and_parses_catalog():
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"data": [{"id": "7", "title": "Penduduk", "url": "https://bps.go.id/id/statistics-table"}], "total": 1})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BPSAdapter(api_key="secret", client=client)

    result = asyncio.run(adapter.search("dynamic", "penduduk", 1))
    asyncio.run(client.aclose())

    request = seen["request"]
    assert str(request.url).startswith("https://webapi.bps.go.id/v1/api/list?")
    assert request.url.params["domain"] == "1306"
    assert request.url.params["key"] == "secret"
    assert request.url.params["model"] == "var"
    assert request.headers["user-agent"].startswith("Marawa-Prototype/1")
    assert result["items"][0]["id"] == "7"


def test_live_adapter_normalizes_http_timeout_auth_and_application_schema_errors():
    async def run(response=None, error=None):
        def handler(request):
            if error:
                raise error
            return response

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        result = await BPSAdapter(api_key="secret", client=client).search("simdasi", "x")
        await client.aclose()
        return result

    timeout = asyncio.run(run(error=httpx.ReadTimeout("late")))
    auth = asyncio.run(run(response=httpx.Response(401, json={})))
    invalid = asyncio.run(run(response=httpx.Response(200, json={"status": "error"})))

    assert timeout == {"error": {"code": "bps_unavailable"}}
    assert auth == {"error": {"code": "bps_auth"}}
    assert invalid == {"error": {"code": "bps_schema_error"}}


def test_live_glossary_500_maps_to_glossary_unavailable():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(500, json={})))

    result = asyncio.run(BPSAdapter(api_key="secret", client=client).glossary("penduduk"))
    asyncio.run(client.aclose())

    assert result == {"error": {"code": "glossary_unavailable"}}
