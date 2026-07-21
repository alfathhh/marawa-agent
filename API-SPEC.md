# API-SPEC.md — Kontrak Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> Base URL browser: `/api/prototype`. Semua endpoint hanya untuk origin lokal terkonfigurasi.
> Tidak ada auth pengguna; otoritas sesi memakai `session_id`, `server_generation`, dan `state_version`.

## 1. Konvensi

### 1.1 Format sukses

Endpoint JSON mengembalikan:

```json
{"data": {"status": "ok"}}
```

Endpoint list boleh menambah `meta`. `DELETE` sukses mengembalikan 204 tanpa body.

### 1.2 Format error

```json
{
  "error": {
    "code": "validation_error",
    "message": "Pesan tidak boleh kosong.",
    "details": {"field": "text"}
  }
}
```

`code` stabil untuk logic client/test. `message` Bahasa Indonesia untuk pengguna. `details` object tertutup per error dan boleh `{}`.

### 1.3 Header dan tipe

- Request/response JSON: `Content-Type: application/json; charset=utf-8`.
- Semua response: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, dan CSP self-only sesuai ARCHITECTURE §10.
- Request `POST`/`DELETE` hanya menerima `Origin` loopback exact yang dikonfigurasi. `Origin` lain atau `Sec-Fetch-Site: cross-site` menghasilkan 403 `origin_not_allowed` sebelum body diproses.
- `session_id`, kode wilayah, upstream ID, nilai Decimal kanonik, dan periode diserialisasi sebagai string.
- Timestamp UTC ISO 8601 berakhiran `Z`.
- Request body maksimum 16 KiB; text maksimum 8.000 karakter setelah NFKC untuk batas panjang.

## 2. Health dan sesi

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/live` | Proses hidup; 200 tanpa mengecek provider eksternal. |
| POST | `/sessions` | Membuat sesi kosong; body harus `{}`. |
| GET | `/sessions/{session_id}` | Memvalidasi sesi/generasi; tidak mengembalikan transcript atau frame internal. |
| DELETE | `/sessions/{session_id}` | Menghapus sesi idempoten; header `X-Server-Generation` wajib bila sesi ada. |

### 2.1 `GET /live`

Response 200:

```json
{
  "data": {
    "status": "ok",
    "app": "marawa-prototype-v1",
    "server_generation": "boot_Jul21A"
  }
}
```

Endpoint tidak mengembalikan status/API key BPS atau LLM.

### 2.2 `POST /sessions`

Request:

```json
{}
```

Response 201:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 0,
    "created_at": "2026-07-21T02:00:00Z",
    "expires_after_idle_seconds": 7200
  }
}
```

Errors: `400 malformed_json`, `413 request_too_large`, `429 session_capacity`, `500 internal_error`.

### 2.3 `GET /sessions/pv1_k7R3mQ8vN2xP5tY9aB4cD6fH`

Header wajib:

```text
X-Server-Generation: boot_Jul21A
```

Response 200:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 4,
    "status": "active",
    "last_active_at": "2026-07-21T02:04:00Z"
  }
}
```

Errors:

- 404 `session_not_found`, details `{}`;
- 409 `generation_mismatch`, details `{"expected_action":"start_new_session"}`;
- 410 `session_expired`, details `{"expected_action":"start_new_session"}`.

### 2.4 `DELETE /sessions/pv1_k7R3mQ8vN2xP5tY9aB4cD6fH`

Header `X-Server-Generation: boot_Jul21A`. Response 204 tanpa body. Sesi tidak ada juga 204. Generation salah → 409 `generation_mismatch`.

## 3. Percakapan

| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/sessions/{session_id}/messages` | Memproses satu turn teks secara serial dan idempoten. |

### 3.1 Request pesan

`POST /sessions/pv1_k7R3mQ8vN2xP5tY9aB4cD6fH/messages`

Headers:

```text
X-Server-Generation: boot_Jul21A
Content-Type: application/json
```

Body:

```json
{
  "message_id": "0f3d31b0-b204-4ed8-bb85-dac9acae8f27",
  "state_version": 0,
  "text": "data jumlah penduduk Padang Pariaman"
}
```

Field tertutup:

| Field | Tipe | Aturan |
|---|---|---|
| `message_id` | UUID string | Wajib; idempotency key per sesi. |
| `state_version` | integer | Wajib; minimum 0; harus sama dengan state server sebelum turn. |
| `text` | string | Wajib; setelah trim 1–8.000 karakter. |

### 3.2 Response kandidat

Response 200:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 1,
    "turn_status": "completed",
    "assistant": {
      "id": "msg_a_001",
      "text": "Saya menemukan beberapa sumber resmi. Pilih salah satu kode berikut, Kak.\n\nSIMDASI\nS1 — Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan\n\nTabel Dinamis\nT1 — Jumlah Penduduk Menurut Kecamatan\n\nPublikasi\nP1 — Kabupaten Padang Pariaman Dalam Angka 2025",
      "actions": [
        {"id": "act_s1", "label": "S1", "value": "S1", "kind": "candidate"},
        {"id": "act_t1", "label": "T1", "value": "T1", "kind": "candidate"},
        {"id": "act_p1", "label": "P1", "value": "P1", "kind": "candidate"},
        {"id": "act_next", "label": "Lihat hasil berikutnya", "value": "next", "kind": "next"}
      ],
      "sources": [
        {"family": "simdasi", "status": "ok"},
        {"family": "dynamic", "status": "ok"},
        {"family": "publication", "status": "ok"}
      ],
      "provenance": []
    }
  }
}
```

`actions` maksimum 12. `sources` selalu memuat tiga family untuk respons pencarian, dengan status `ok|empty|error`. `provenance` hanya memuat fakta yang benar-benar dipakai.

### 3.3 Response pilihan periode

Request setelah memilih `S1`:

```json
{
  "message_id": "89781679-25f6-4f30-a6d6-a72a5dbe2db8",
  "state_version": 1,
  "text": "S1"
}
```

Response 200:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 2,
    "turn_status": "completed",
    "assistant": {
      "id": "msg_a_002",
      "text": "Sumber S1 tersedia untuk periode berikut. Pilih periodenya sebelum saya mengambil data:\n• 2024\n• 2023",
      "actions": [
        {"id": "act_2024", "label": "2024", "value": "2024", "kind": "period"},
        {"id": "act_2023", "label": "2023", "value": "2023", "kind": "period"}
      ],
      "sources": [{"family": "simdasi", "status": "ok"}],
      "provenance": [
        {
          "kind": "catalog",
          "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
          "source_type": "Web API BPS - SIMDASI",
          "url": "https://padangpariamankab.bps.go.id/id/statistics-table"
        }
      ]
    }
  }
}
```

### 3.4 Response data

Request:

```json
{
  "message_id": "40805d90-11c9-4292-9237-c9ecadfaacb0",
  "state_version": 2,
  "text": "2024"
}
```

Response fixture 200:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 3,
    "turn_status": "completed",
    "assistant": {
      "id": "msg_a_003",
      "text": "Jumlah Penduduk Kabupaten Padang Pariaman pada 2024: 434.514 jiwa.\nIndikator: Jumlah Penduduk\nSumber: Web API BPS - SIMDASI — Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan\nhttps://padangpariamankab.bps.go.id/id/statistics-table",
      "actions": [],
      "sources": [{"family": "simdasi", "status": "ok"}],
      "provenance": [
        {
          "kind": "verified_row",
          "row_ref": "row_penduduk_2024",
          "display_value": "434.514",
          "unit": "jiwa",
          "period": "2024",
          "coverage": "Kabupaten Padang Pariaman",
          "indicator": "Jumlah Penduduk",
          "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
          "source_type": "Web API BPS - SIMDASI",
          "url": "https://padangpariamankab.bps.go.id/id/statistics-table"
        }
      ]
    }
  }
}
```

Nilai ini fixture test sesuai PRD §4.4, bukan bukti nilai live.

### 3.5 Response analisis

Request:

```json
{
  "message_id": "fd8b8c55-00f0-4dbe-9199-d5d5037da7f4",
  "state_version": 3,
  "text": "bandingkan dengan 2023"
}
```

Response fixture 200:

```json
{
  "data": {
    "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
    "server_generation": "boot_Jul21A",
    "state_version": 4,
    "turn_status": "completed",
    "assistant": {
      "id": "msg_a_004",
      "text": "Jumlah Penduduk Kabupaten Padang Pariaman naik dari 430.000 jiwa pada 2023 menjadi 434.514 jiwa pada 2024.\nSelisih = 434.514 − 430.000 = 4.514 jiwa.\nPerubahan = 4.514 ÷ 430.000 × 100 = 1,05%.\nSumber: Web API BPS - SIMDASI — Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan\nhttps://padangpariamankab.bps.go.id/id/statistics-table",
      "actions": [],
      "sources": [{"family": "simdasi", "status": "ok"}],
      "provenance": [
        {
          "kind": "derived",
          "start_row_ref": "row_penduduk_2023",
          "end_row_ref": "row_penduduk_2024",
          "difference": "4.514",
          "percent_change": "1,05",
          "direction": "naik",
          "unit": "jiwa",
          "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
          "url": "https://padangpariamankab.bps.go.id/id/statistics-table"
        }
      ]
    }
  }
}
```

### 3.6 Errors endpoint pesan

| HTTP | Code | Kapan | Details |
|---:|---|---|---|
| 400 | `malformed_json` | JSON tidak dapat diparse. | `{}` |
| 409 | `state_version_conflict` | Versi request bukan versi server. | `{"current_state_version":4}` |
| 409 | `generation_mismatch` | Server restart/generasi berbeda. | `{"expected_action":"start_new_session"}` |
| 410 | `session_expired` | Idle > 2 jam. | `{"expected_action":"start_new_session"}` |
| 413 | `request_too_large` | Body > 16 KiB. | `{"maximum_bytes":16384}` |
| 422 | `validation_error` | UUID/version/text invalid. | `{"field":"text"}` atau field terkait |
| 429 | `turn_rate_limited` | > 20 turn/jam pada sesi. | `{"retry_after_seconds":3600}` |
| 500 | `internal_error` | Bug internal sebelum fallback aman. | `{"reference":"err_local_001"}` |
| 503 | `agent_unavailable` | Provider LLM gagal dan router fallback juga gagal. | `{"actions":["handover","guestbook"]}` |

Tool/sumber gagal normalnya **bukan** HTTP error; response 200 membawa fallback user-facing dan `sources.status=error`. Ini menjaga transcript tetap konsisten.

## 4. Kontrak tool internal

Tool tidak dapat dipanggil browser. Semua schema `strict=true`, `additionalProperties=false`, dan tidak memiliki `domain`.

### 4.1 Registry

| Tool | Input model | Output normal | Gate utama |
|---|---|---|---|
| `bps_search_catalogs` | `keyword:string`, `page:integer` | Tiga group kandidat + pagination | intent data; `page` integer 1–6 |
| `bps_list_periods` | `candidate_code:string`, `page:integer` | Maksimum 20 `PeriodOption` per halaman | code pernah ditawarkan; hanya S/T; page 1–10 |
| `bps_get_selected_data` | `candidate_code:string`, `period:string`, `coverage:string|null`, `category:string|null` | VerifiedRow[] | code+period offered; S/T; domain injected |
| `glossary_search` | `query:string` | Maks 3 definisi resmi | query 1–500 karakter |
| `kb_search` | `query:string` | Maks 4 chunk verified | dokumen `verified=true` |
| `compare_verified_rows` | `start_row_ref:string`, `end_row_ref:string` | DerivedResult | refs frame aktif + comparable |
| `mock_handover` | `action:string` | status mock + action | action enum tertutup |

### 4.2 `bps_search_catalogs`

Input:

```json
{"keyword":"jumlah penduduk","page":1}
```

`keyword` setelah trim 1–500 karakter. `page` integer 1–6; halaman di luar rentang menghasilkan `invalid_page`. Maksimum kandidat kumulatif satu frame adalah 54 (6 halaman × 3 sumber × 3 kandidat).

Output fixture:

```json
{
  "found": true,
  "search_id": "search_penduduk_01",
  "groups": [
    {
      "source": "simdasi",
      "label": "SIMDASI",
      "status": "ok",
      "has_more": true,
      "items": [
        {
          "code": "S1",
          "id": "tb_penduduk_01",
          "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
          "subject": "Kependudukan",
          "periods": ["2024", "2023"],
          "abstract": null,
          "url": "https://padangpariamankab.bps.go.id/id/statistics-table"
        }
      ]
    },
    {
      "source": "dynamic",
      "label": "Tabel Dinamis",
      "status": "ok",
      "has_more": false,
      "items": [
        {
          "code": "T1",
          "id": "42",
          "title": "Jumlah Penduduk Menurut Kecamatan",
          "subject": "Kependudukan",
          "periods": [],
          "abstract": null,
          "url": "https://padangpariamankab.bps.go.id/id/statistics-table"
        }
      ]
    },
    {
      "source": "publication",
      "label": "Publikasi",
      "status": "ok",
      "has_more": false,
      "items": [
        {
          "code": "P1",
          "id": "https://padangpariamankab.bps.go.id/id/publication/2025/02/28/b35cba34a99c4e94f74c9f0a/kabupaten-padang-pariaman-dalam-angka-2025.html",
          "title": "Kabupaten Padang Pariaman Dalam Angka 2025",
          "subject": null,
          "periods": [],
          "abstract": "Publikasi tahunan yang menyajikan gambaran Kabupaten Padang Pariaman.",
          "url": "https://padangpariamankab.bps.go.id/id/publication/2025/02/28/b35cba34a99c4e94f74c9f0a/kabupaten-padang-pariaman-dalam-angka-2025.html"
        }
      ]
    }
  ],
  "source_errors": []
}
```

Error object tertutup: `invalid_query`, `invalid_page`, `bps_unavailable`, `bps_auth`, `bps_rate_limit`, `bps_schema_error`. Partial failure masuk `source_errors` dan group terkait `status=error`.

### 4.3 `bps_list_periods`

Input:

```json
{"candidate_code":"S1","page":1}
```

Output:

```json
{
  "candidate_code": "S1",
  "page": 1,
  "total": 2,
  "items": [
    {"value": "2024", "upstream_id": "2024", "label": "2024"},
    {"value": "2023", "upstream_id": "2023", "label": "2023"}
  ],
  "has_more": false
}
```

`page` integer 1–10. Maksimum 20 item per response. Item dari halaman yang berhasil dirender ditambahkan ke `offered_periods`; halaman baru tidak menghapus periode lama. Errors: `candidate_not_found`, `selection_required`, `source_not_numeric`, `invalid_page`, `periods_unavailable`, `bps_unavailable`, `bps_schema_error`.

### 4.4 `bps_get_selected_data`

Input:

```json
{
  "candidate_code": "S1",
  "period": "2024",
  "coverage": "Kabupaten Padang Pariaman",
  "category": null
}
```

Output ringkas; object tiap row mengikuti DATABASE §3.6:

```json
{
  "answerable": true,
  "metadata": {"complete": true, "missing": []},
  "candidate_code": "S1",
  "period": "2024",
  "rows": [
    {
      "row_ref": "row_penduduk_2024",
      "indicator": "Jumlah Penduduk",
      "display_value": "434.514",
      "value_decimal": "434514",
      "unit": "jiwa",
      "period": "2024",
      "coverage": "Kabupaten Padang Pariaman",
      "coverage_code": "1306",
      "source_title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
      "source_type": "Web API BPS - SIMDASI",
      "source_url": "https://padangpariamankab.bps.go.id/id/statistics-table"
    }
  ],
  "total_rows": 1,
  "truncated": false
}
```

Errors: `candidate_not_found`, `selection_required`, `period_selection_required`, `period_not_available`, `dimension_not_found`, `ambiguous_dimension`, `scope_domain_not_allowed`, `metadata_incomplete`, `data_not_found`, `bps_unavailable`, `bps_auth`, `bps_rate_limit`, `bps_schema_error`.

### 4.5 `glossary_search`

Input:

```json
{"query":"penduduk"}
```

Output fixture:

```json
{
  "found": true,
  "items": [
    {
      "source_ref": "glossary_4406",
      "concept": "Penduduk",
      "indicator_title": "",
      "definition": "Orang yang berdomisili di suatu wilayah menurut konsep kependudukan sumber resmi.",
      "unit": "",
      "source_content": "Glosarium Web API BPS",
      "source_url": "https://webapi.bps.go.id/documentation/#glosarium"
    }
  ]
}
```

Teks definisi di atas adalah fixture kontrak, bukan kutipan live. Errors: `invalid_query`, `glossary_unavailable`, `glossary_schema_error`. `found=false, items=[]` adalah no-match, bukan error.

### 4.6 `kb_search`

Input:

```json
{"query":"bagaimana konsultasi statistik"}
```

Output:

```json
{
  "found": true,
  "chunks": [
    {
      "source_ref": "kb_pst_services_konsultasi",
      "source_key": "pst_services",
      "title": "Layanan PST BPS Kabupaten Padang Pariaman",
      "heading": "Konsultasi Statistik",
      "text": "Konsultasi statistik dapat dibantu oleh petugas PST. Prototype menawarkan admin mock dan Buku Tamu untuk tindak lanjut.",
      "source_url": "https://pst.bps.go.id",
      "verified_by": "PIC PST",
      "verified_at": "2026-07-21"
    }
  ]
}
```

Errors: `invalid_query`, `kb_unavailable`, `kb_schema_error`. Dokumen unverified tidak muncul.

### 4.7 `compare_verified_rows`

Input:

```json
{"start_row_ref":"row_penduduk_2023","end_row_ref":"row_penduduk_2024"}
```

Output:

```json
{
  "start_row_ref": "row_penduduk_2023",
  "end_row_ref": "row_penduduk_2024",
  "start_display": "430.000",
  "end_display": "434.514",
  "unit": "jiwa",
  "difference_decimal": "4514",
  "difference_display": "4.514",
  "percent_decimal": "1.049767441860465116279069767",
  "percent_display": "1,05",
  "direction": "naik",
  "formula": "(434514 - 430000) / 430000 × 100"
}
```

Errors: `row_not_found`, `rows_not_comparable` dengan details reason `indicator|unit|coverage|period|unverified`, dan `zero_baseline`.

### 4.8 `mock_handover`

Input action enum `offer_admin|simulate_unavailable|decline_wait|guestbook`.

```json
{"action":"simulate_unavailable"}
```

Output:

```json
{
  "status": "admin_unavailable",
  "is_mock": true,
  "message": "Prototype ini belum tersambung ke petugas.",
  "guestbook_url": "https://s.bps.go.id/tamu1306"
}
```

Errors: `invalid_handover_action`.

## 5. Hal yang sengaja tidak memiliki endpoint

- Tidak ada `/chat` umum di luar namespace prototype.
- Tidak ada endpoint langsung untuk BPS/Glosarium/KB/analysis; browser hanya mengirim pesan.
- Tidak ada auth, dashboard, admin, user management, settings, webhook, Evolution, file upload, transcript export, atau SIRuSa.
- Tidak ada endpoint introspeksi state/frame/tool trace untuk browser.

## 6. Status turn dan source

`turn_status` tertutup: `completed`, `blocked`, `degraded`, `truncated`, `failed`, `cancelled`.

Source family tertutup: `simdasi`, `dynamic`, `publication`, `glossary`, `knowledge_base`. Source status tertutup: `ok`, `empty`, `error`.

`assistant.provenance[].kind` tertutup:

| Kind | Klaim yang diotorisasi | Field minimum |
|---|---|---|
| `catalog` | Judul/jenis/URL kandidat, bukan angka statistik | `title`, `source_type`, `url` |
| `publication_metadata` | Judul, abstraksi/status kosong, URL; bukan angka statistik | `title`, `url` |
| `verified_row` | Observasi data resmi S/T | `row_ref`, `display_value`, `unit`, `period`, `coverage`, `indicator`, `title`, `source_type`, `url` |
| `knowledge` | Definisi/prosedur Glosarium/KB termasuk `sourced_knowledge` | `source_ref`, `title`, `context`, `url` nullable |
| `derived` | Selisih/persen/arah runtime | dua row ref, hasil, unit, title, URL |

`provenance` maksimum 20 item per turn. Kind lain ditolak output gate.

## 7. HTTP status

| Status | Makna |
|---:|---|
| 200 | Read/turn sukses, termasuk fallback sumber yang user-facing. |
| 201 | Sesi dibuat. |
| 204 | Delete idempoten. |
| 400 | JSON malformed. |
| 403 | Origin/cross-site request tidak diizinkan. |
| 404 | Sesi tidak ditemukan. |
| 409 | Version/generation conflict. |
| 410 | Sesi expired. |
| 413 | Payload terlalu besar. |
| 422 | Field valid secara JSON tetapi melanggar schema. |
| 429 | Kapasitas/rate limit. |
| 500 | Bug internal yang tidak dapat dirender aman. |
| 503 | Agent dan fallback router unavailable. |

## 8. Daftar kode error tertutup

`malformed_json`, `request_too_large`, `validation_error`, `origin_not_allowed`, `session_not_found`, `session_expired`, `generation_mismatch`, `state_version_conflict`, `session_capacity`, `turn_rate_limited`, `internal_error`, `agent_unavailable`, `unknown_tool`, `invalid_arguments`, `invalid_query`, `invalid_page`, `candidate_not_found`, `selection_required`, `source_not_numeric`, `periods_unavailable`, `period_selection_required`, `period_not_available`, `dimension_not_found`, `ambiguous_dimension`, `scope_domain_not_allowed`, `metadata_incomplete`, `data_not_found`, `bps_unavailable`, `bps_auth`, `bps_rate_limit`, `bps_schema_error`, `glossary_unavailable`, `glossary_schema_error`, `kb_unavailable`, `kb_schema_error`, `row_not_found`, `rows_not_comparable`, `zero_baseline`, `invalid_handover_action`, `loop_budget_exceeded`, `duplicate_tool_call`.
