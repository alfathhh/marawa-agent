from prototype_v1.guardrails import (
    DOMAIN, Provenance, gate_domain, official_url, sanitize, validate_metadata,
)
from prototype_v1.scope import TerritoryRegistry


def test_provenance_requires_complete_verified_metadata_and_rejects_publication():
    row = {"value_decimal":"10", "display_value":"10", "unit":"jiwa", "period":"2024", "coverage":"Kabupaten", "coverage_code":"1306", "indicator":"Penduduk", "source_title":"Data", "source_type":"simdasi", "source_url":"https://padangpariamankab.bps.go.id/a", "source_family":"publication", "answerable":True, "metadata_complete":True}
    assert validate_metadata(row) == ["source_family"]
    assert Provenance("sourced_knowledge", "ref-1", "chunk").kind == "sourced_knowledge"


def test_scope_requires_exact_code_label_and_ancestor():
    registry = TerritoryRegistry([{"code":"1306010", "name":"Kecamatan X", "ancestor":"1306"}], verified=True)
    assert registry.accepts("1306010", "Kecamatan X")
    assert not registry.accepts("130601", "Kecamatan X")
    assert not registry.accepts("1306010", "Kecamatan X<script>")


def test_guardrails_sanitize_and_allow_only_official_https_urls():
    assert sanitize("Ａ<script>alert(1)</script><b>15+</b>\x00\u202e") == "A15+"
    assert sanitize("&lt;script&gt;alert(1)&lt;/script&gt;aman") == "aman"
    assert official_url("https://bps.go.id/x")
    assert official_url("https://s.bps.go.id/tamu1306", guestbook=True)
    assert not official_url("http://evil.example/x")
    assert not official_url("https://evil.bps.go.id.evil/x")
    assert not official_url("https://bps.go.id:444/x")
    assert not official_url("https://s.bps.go.id/tamu1306?x=1", guestbook=True)


def test_domain_is_runtime_injected_and_supplied_domain_rejected():
    from prototype_v1.guardrails import prepare_tool_args

    assert DOMAIN == "1306"
    assert gate_domain({"domain":"1371"})["error"]["code"] == "scope_domain_not_allowed"
    assert gate_domain({"query":"x"}) is None
    assert prepare_tool_args({"query":"x"}, {"query"}) == {"query":"x", "domain":"1306"}
    assert prepare_tool_args({"query":"x", "extra":1}, {"query"}) == {"error":{"code":"invalid_arguments"}}


def test_safe_error_never_contains_exception_details():
    from prototype_v1.guardrails import safe_error
    assert safe_error("internal_error") == {"error":{"code":"internal_error"}}
