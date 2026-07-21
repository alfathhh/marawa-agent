from decimal import Decimal

import pytest

from prototype_v1.data_parsers import parse_dynamic, parse_simdasi


BASE = {
    "title": "Kemiskinan Kabupaten Padang Pariaman 2024",
    "indicator": "Jumlah penduduk miskin",
    "unit": "Jiwa",
    "period": "2024",
    "coverage": "Kabupaten Padang Pariaman",
    "coverage_code": "1306",
    "value": "434514",
    "source_url": "https://padangpariamankab.bps.go.id/id/statistics-table/1",
}


def test_simdasi_builds_complete_verified_row():
    result = parse_simdasi(BASE)

    assert result == {"rows": [{
        "value_decimal": Decimal("434514"), "display_value": "434.514", "unit": "Jiwa",
        "period": "2024", "coverage": "Kabupaten Padang Pariaman", "coverage_code": "1306",
        "indicator": "Jumlah penduduk miskin", "source_title": BASE["title"],
        "source_type": "SIMDASI", "source_url": BASE["source_url"], "source_family": "simdasi",
        "answerable": True, "metadata_complete": True, "metadata_missing": [],
    }]}


@pytest.mark.parametrize("field", ["title", "indicator", "unit", "period", "coverage", "value", "source_url"])
def test_simdasi_rejects_each_incomplete_field(field):
    payload = {**BASE, field: ""}

    result = parse_simdasi(payload)

    expected = "source_title" if field == "title" else "value_decimal" if field == "value" else field
    assert result == {"error": {"code": "metadata_incomplete", "details": {"missing": [expected]}}}


def test_simdasi_rejects_foreign_domain_and_malformed_value():
    assert parse_simdasi({**BASE, "coverage_code": "1307"})["error"]["code"] == "scope_mismatch"
    assert parse_simdasi({**BASE, "value": "not-a-number"})["error"]["code"] == "bps_schema_error"


def dynamic_payload():
    return {
        "title": "Tabel Penduduk", "indicator": "Jumlah penduduk", "unit": "Jiwa",
        "period": "2024", "source_url": "https://bps.go.id/id/statistics-table/2",
        "dimensions": [
            {"id": "wilayah", "values": {"1306": "Kabupaten Padang Pariaman", "1307": "Kabupaten Solok"}},
            {"id": "tahun", "values": {"2024": "2024"}},
            {"id": "jenis", "values": {"total": "Total"}},
        ],
        "dimension_order": ["wilayah", "tahun", "jenis"],
        "datacontent": {"1306|2024|total": "434514", "1307|2024|total": "999"},
    }


def test_dynamic_parses_dimension_keys_without_positional_slicing_and_filters_domain():
    result = parse_dynamic(dynamic_payload())

    assert len(result["rows"]) == 1
    assert result["rows"][0]["value_decimal"] == Decimal("434514")
    assert result["rows"][0]["display_value"] == "434.514"
    assert result["rows"][0]["coverage_code"] == "1306"


def test_dynamic_rejects_unknown_dimension_member_and_empty_domain_rows():
    malformed = dynamic_payload()
    malformed["datacontent"] = {"1306|2024|missing": "1"}
    assert parse_dynamic(malformed)["error"]["code"] == "bps_schema_error"

    foreign = dynamic_payload()
    foreign["datacontent"] = {"1307|2024|total": "1"}
    assert parse_dynamic(foreign) == {"error": {"code": "data_not_found"}}


def test_dynamic_rejects_incomplete_metadata():
    payload = dynamic_payload()
    payload["unit"] = ""

    assert parse_dynamic(payload) == {"error": {"code": "metadata_incomplete", "details": {"missing": ["unit"]}}}


def test_parsers_report_no_data():
    assert parse_simdasi({**BASE, "rows": []}) == {"error": {"code": "data_not_found"}}
    payload = dynamic_payload()
    payload["datacontent"] = {}
    assert parse_dynamic(payload) == {"error": {"code": "data_not_found"}}


def test_dynamic_supports_explicit_dimension_mapping_keys():
    payload = dynamic_payload()
    payload["datacontent"] = [{"dimensions": {"jenis": "total", "wilayah": "1306", "tahun": "2024"}, "value": "12.50"}]

    row = parse_dynamic(payload)["rows"][0]

    assert row["value_decimal"] == Decimal("12.50")
    assert row["display_value"] == "12,50"


def test_publication_payload_is_not_accepted_as_numeric_data():
    assert parse_simdasi({**BASE, "source_family": "publication"})["error"]["code"] == "bps_schema_error"
