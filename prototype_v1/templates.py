TEMPLATES = {
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


def render(name):
    return TEMPLATES[name]


# Backward-compatible exports; handover rules have one home.
from prototype_v1.handover import GUESTBOOK_URL, mock_handover  # noqa: E402, F401
