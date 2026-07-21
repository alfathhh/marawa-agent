from decimal import Decimal

from prototype_v1.models import Candidate, SearchFrame
from prototype_v1.renderers import render_data, render_publication


ROW = {
    "indicator": "Jumlah penduduk miskin", "display_value": "434.514", "value_decimal": Decimal("434514"),
    "unit": "Jiwa", "period": "2024", "coverage": "Kabupaten Padang Pariaman",
    "coverage_code": "1306", "source_title": "Kemiskinan 2024", "source_type": "SIMDASI",
    "source_url": "https://padangpariamankab.bps.go.id/id/statistics-table/1",
}


def test_data_renderer_has_exact_eight_provenance_elements():
    text = render_data([ROW])

    assert text == (
        "Indikator: Jumlah penduduk miskin\n"
        "Nilai: 434.514\nSatuan: Jiwa\nPeriode: 2024\n"
        "Cakupan: Kabupaten Padang Pariaman (1306)\n"
        "Judul sumber: Kemiskinan 2024\nJenis sumber: SIMDASI\n"
        "URL sumber: https://padangpariamankab.bps.go.id/id/statistics-table/1\n"
        "Total data: 1."
    )


def test_data_renderer_limits_rows_and_discloses_total_and_truncation():
    rows = [{**ROW, "display_value": str(index)} for index in range(18)]

    text = render_data(rows)

    assert text.count("Indikator:") == 10
    assert "Total data: 18. Ditampilkan 10; rincian lainnya tersedia." in text
    assert "Nilai: 10\n" not in text


def test_publication_renderer_is_metadata_only_and_does_not_change_frame_rows():
    frame = SearchFrame("x", "q", "q", verified_rows={"r1": ROW})
    candidate = Candidate("P1", "publication", "1", "Sensus 2020", "https://bps.go.id/id/publication/1", abstract="Ringkasan resmi.")

    result = render_publication(candidate, frame)

    assert result == {
        "text": "Judul: Sensus 2020\nAbstraksi: Ringkasan resmi.\nBaca/unduh: https://bps.go.id/id/publication/1",
        "provenance": {"kind": "structural", "source_url": candidate.url},
    }
    assert frame.verified_rows == {"r1": ROW}


def test_publication_renderer_uses_exact_missing_abstract_text():
    candidate = Candidate("P1", "publication", "1", "Sensus", "https://bps.go.id/id/publication/1")

    result = render_publication(candidate)

    assert "Abstraksi: Abstraksi tidak tersedia pada metadata BPS." in result["text"]


def test_publication_renderer_rejects_non_publication_and_unofficial_url():
    numeric = Candidate("S1", "simdasi", "1", "Data", "https://bps.go.id/id/table/1")
    foreign = Candidate("P1", "publication", "1", "Doc", "https://example.com/doc")

    assert render_publication(numeric)["error"]["code"] == "source_not_publication"
    assert render_publication(foreign)["error"]["code"] == "invalid_source_url"
