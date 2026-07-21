from decimal import Decimal

import pytest

from prototype_v1.analysis import compare_rows, format_id, render_analysis


def row(period="2023", value="430000", **changes):
    base = {
        "row_ref": f"row-{period}",
        "answerable": True,
        "metadata_complete": True,
        "metadata_missing": [],
        "provenance": "verified",
        "indicator_id": "population",
        "indicator": "Jumlah Penduduk",
        "unit": "jiwa",
        "coverage_code": "1306",
        "coverage": "Kabupaten Padang Pariaman",
        "period": period,
        "value_decimal": value,
        "display_value": format_id(value),
        "source_title": "SIMDASI BPS",
        "source_type": "SIMDASI",
        "source_url": "https://padangpariamankab.bps.go.id/data",
    }
    return {**base, **changes}


def test_computes_decimal_difference_percent_and_direction():
    result = compare_rows(row(), row("2024", "434514"))

    assert result["difference_decimal"] == "4514.00"
    assert result["difference_display"] == "4.514,00"
    assert result["percent_decimal"] == "1.05"
    assert result["percent_display"] == "1,05"
    assert result["direction"] == "naik"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"indicator_id": "poverty"}, "indicator"),
        ({"unit": "persen"}, "unit"),
        ({"coverage_code": "1306010"}, "coverage"),
        ({"period": "2023"}, "period"),
    ],
)
def test_rejects_non_comparable_rows(changes, reason):
    end = row("2024")
    end.update(changes)

    result = compare_rows(row(), end)

    assert result == {
        "error": {"code": "rows_not_comparable", "details": {"reason": reason}}
    }


def test_rejects_unverified_or_unregistered_rows_without_derived_values():
    assert compare_rows(None, row("2024")) == {"error": {"code": "row_not_found"}}
    result = compare_rows(row(answerable=False), row("2024"))

    assert result == {
        "error": {"code": "rows_not_comparable", "details": {"reason": "unverified"}}
    }
    assert "difference_decimal" not in result


def test_rejects_float_and_noncanonical_decimal_values():
    for invalid in (1234.56, "1.234,56", "01", "NaN", "Infinity"):
        result = compare_rows(row(value_decimal=invalid), row("2024"))

        assert result["error"]["code"] == "rows_not_comparable"
        assert result["error"]["details"]["reason"] == "invalid_value"


def test_rounds_difference_and_percentage_half_up_to_two_decimals():
    result = compare_rows(row(value="1.005"), row("2024", "2.010"))

    assert result["difference_decimal"] == "1.01"
    assert result["percent_decimal"] == "100.00"


def test_zero_baseline_has_no_derived_values():
    result = compare_rows(row(value="0"), row("2024", "10"))

    assert result == {"error": {"code": "zero_baseline"}}


@pytest.mark.parametrize(
    ("end", "difference", "percent", "direction"),
    [("75", "-25.00", "-25.00", "turun"), ("100", "0.00", "0.00", "tetap")],
)
def test_direction_comes_from_decimal_difference(end, difference, percent, direction):
    result = compare_rows(row(value="100"), row("2024", end))

    assert (result["difference_decimal"], result["percent_decimal"], result["direction"]) == (
        difference,
        percent,
        direction,
    )


def test_formats_canonical_decimal_as_indonesian():
    assert format_id("1234.56") == "1.234,56"


def test_renderer_is_deterministic_and_contains_complete_provenance():
    start, end = row(), row("2024", "434514")
    result = compare_rows(start, end)

    rendered = render_analysis(result, start, end)

    assert rendered == (
        "Jumlah Penduduk — Kabupaten Padang Pariaman\n"
        "Nilai awal (2023): 430.000 jiwa\n"
        "Nilai akhir (2024): 434.514 jiwa\n"
        "Rumus selisih: 434514 - 430000 = 4.514,00 jiwa\n"
        "Rumus persen: (434514 - 430000) / 430000 × 100 = 1,05%\n"
        "Arah: naik\n"
        "Sumber awal [row-2023]: SIMDASI BPS (SIMDASI) — https://padangpariamankab.bps.go.id/data\n"
        "Sumber akhir [row-2024]: SIMDASI BPS (SIMDASI) — https://padangpariamankab.bps.go.id/data\n"
        "Provenance: derived dari verified rows row-2023 dan row-2024."
    )
    assert result["provenance"] == {
        "kind": "derived",
        "source_refs": ["row-2023", "row-2024"],
    }


def test_renderer_rejects_error_results():
    with pytest.raises(ValueError, match="successful derived result"):
        render_analysis({"error": {"code": "zero_baseline"}}, row(), row("2024"))


def test_result_uses_decimal_objects_internally_only(monkeypatch):
    result = compare_rows(row(value="0.1"), row("2024", "0.2"))

    assert Decimal(result["difference_decimal"]) == Decimal("0.10")
    assert result["percent_decimal"] == "100.00"
    assert not any(isinstance(value, float) for value in result.values())
