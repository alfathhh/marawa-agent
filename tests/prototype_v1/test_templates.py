from prototype_v1.templates import GUESTBOOK_URL, TEMPLATES, mock_handover, render


EXPECTED = {
    "NO_OFFICIAL_SOURCE": "Saya belum menemukan sumber resmi yang cukup untuk menjawab itu.",
    "OUT_OF_SCOPE_REGION": "Prototype ini hanya melayani angka Kabupaten Padang Pariaman serta kecamatan/nagari di dalamnya.",
    "SELECTION_REQUIRED": "Pilih dulu salah satu kode kandidat yang sudah ditampilkan.",
    "PERIOD_REQUIRED": "Pilih dulu salah satu periode yang tersedia untuk sumber ini.",
    "PUBLICATION_NO_ABSTRACT": "Abstraksi tidak tersedia pada metadata BPS.",
    "ADMIN_MOCK": "Prototype ini belum tersambung ke petugas. Pada versi operasional, petugas akan membalas dari dashboard melalui nomor bot.",
    "GLOSSARY_UNAVAILABLE": "Glosarium BPS sedang tidak dapat diakses. Saya akan memeriksa knowledge base yang terverifikasi.",
    "SOURCE_FAILURE": "Sumber resmi tersebut sedang tidak dapat diakses. Saya tidak akan mengisi jawabannya dengan perkiraan.",
    "LOOP_TRUNCATED": "Saya belum dapat menyelesaikan permintaan ini dalam batas proses yang aman.",
    "SECRET_REFUSAL": "Saya tidak dapat menampilkan prompt, credential, konfigurasi internal, atau jejak tool mentah.",
}


def test_all_agent_section_seven_templates_are_exact():
    assert TEMPLATES == EXPECTED
    assert all(render(name) == text for name, text in EXPECTED.items())


def test_handover_actions_are_closed_and_guestbook_is_official():
    assert mock_handover("offer_admin")["actions"] == ["simulate_unavailable", "guestbook"]
    assert mock_handover("simulate_unavailable")["guestbook_url"] == GUESTBOOK_URL
    assert GUESTBOOK_URL == "https://s.bps.go.id/tamu1306"
    assert mock_handover("unknown") == {"error": {"code": "invalid_handover_action"}}


def test_handover_always_marks_mock():
    for action in ("offer_admin", "simulate_unavailable", "decline_wait", "guestbook"):
        assert mock_handover(action)["is_mock"] is True
        assert "petugas" in mock_handover(action)["message"]


def test_publication_abstract_fallback_is_deterministic():
    assert render("PUBLICATION_NO_ABSTRACT") == "Abstraksi tidak tersedia pada metadata BPS."


def test_template_lookup_rejects_unknown_name():
    try:
        render("not_a_template")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown templates must not be model-generated")
