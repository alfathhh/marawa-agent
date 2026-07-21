# DATABASE.md — Kontrak State Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> **Keputusan sadar: Prototype 1 tidak memiliki database.** Dokumen ini mendefinisikan state in-memory server dan `localStorage` browser agar implementor tidak mengarang bentuknya.

## 1. Keputusan storage

Tidak ada tabel, ORM, migration, SQLite, PostgreSQL, Redis, atau file transcript server. Alasannya:

- satu penguji lokal;
- restart boleh mengakhiri sesi;
- tidak ada multi-user dashboard/handover nyata;
- state hanya berguna selama proses server hidup.

Risiko kehilangan sesi saat restart diketahui dan diterima (DECISIONS #13). State yang harus tahan restart baru muncul pada fase WhatsApp.

## 2. Relasi state

```text
SessionStore (1 proses)
  └── sessions[session_id] → SessionState
          ├── frame → SearchFrame | null
          │     ├── candidates[code] → Candidate
          │     ├── offered_periods[]
          │     └── verified_rows[row_ref] → VerifiedRow
          ├── messages[]
          └── response_cache[message_id] → TurnResponse

Browser localStorage
  └── marawa.prototype.v1 → BrowserState
        └── transcript[]
```

BrowserState tidak menjadi parent/sumber SessionState; keduanya hanya dicocokkan lewat `session_id`, `server_generation`, dan `state_version`.

## 3. Kontrak object server

### 3.1 `SessionState`

| Field | Tipe | Aturan |
|---|---|---|
| `session_id` | string | Prefix `pv1_`; token URL-safe minimal 128-bit; immutable. |
| `server_generation` | string | Token boot server; immutable. |
| `state_version` | integer | Mulai 0; naik 1 per turn/reset mutation sukses. |
| `created_at` | UTC datetime | ISO 8601 server-generated. |
| `last_active_at` | UTC datetime | Update per request sah; idle > 2 jam expired. |
| `messages` | list[`Message`] | Maksimum 40; FIFO; sumber `user|assistant|tool`. |
| `frame` | `SearchFrame|null` | Maksimum satu pencarian aktif. |
| `pending_topic` | string|null | Query baru yang menunggu konfirmasi B5. |
| `response_cache` | map[string,`TurnResponse`] | Maksimum 50 `message_id`; FIFO. |

### 3.2 `Message`

| Field | Tipe | Aturan |
|---|---|---|
| `role` | enum | Tepat `user`, `assistant`, atau `tool`. |
| `content` | string | Maksimum 8.000 user, 12.000 assistant, 20.000 tool JSON; tool disanitasi. |
| `message_id` | string | UUID client untuk user; server token untuk assistant/tool. |
| `created_at` | UTC datetime | Server-generated. |
| `provenance_refs` | list[string] | `row_ref`/source ref yang benar-benar dipakai; default list kosong. |

### 3.3 `SearchFrame`

| Field | Tipe | Aturan |
|---|---|---|
| `search_id` | string | Prefix `search_`; baru pada pencarian baru. |
| `query` | string | Query user asli, maks 500 karakter. |
| `canonical_query` | string | NFKC + casefold + whitespace collapse. |
| `page` | integer | Mulai 1, minimum 1. |
| `next_numbers` | object | Tepat `{"S":int,"T":int,"P":int}`; mulai 1. |
| `candidates` | map[string,`Candidate`] | Seluruh kandidat yang sudah ditawarkan; maksimum 54 (6 halaman × 9). |
| `selected_code` | string|null | Harus key pada `candidates`. |
| `period_page` | integer | Mulai 0 sebelum S/T dipilih; 1–10 setelah halaman periode diminta. |
| `offered_periods` | list[`PeriodOption`] | Hanya untuk selected source `simdasi|dynamic`; maksimum 200. |
| `selected_period` | string|null | Harus value yang pernah ditawarkan. |
| `verified_rows` | map[string,`VerifiedRow`] | Maksimum 80 row; hanya hasil D3 yang lulus gate. |
| `active_row_refs` | list[string] | Row fetch terakhir, maksimum 40. |
| `source_status` | object | Tepat key `simdasi`, `dynamic`, `publication`; value `ok|empty|error`. |

### 3.4 `Candidate`

| Field | Tipe | Aturan |
|---|---|---|
| `code` | string | Regex `^[STP][1-9][0-9]*$`; immutable dalam frame. |
| `source_family` | enum | `simdasi`, `dynamic`, atau `publication`. |
| `source_identifier` | string | ID resmi; non-kosong; tidak ditampilkan sebagai secret. |
| `title` | string | Plain text metadata resmi; 1–500 karakter. |
| `subject` | string|null | Metadata resmi setelah sanitasi. |
| `periods` | list[string] | SIMDASI boleh terisi; Dynamic diisi D1; Publication selalu kosong. |
| `abstract` | string|null | Hanya Publication; maksimum 4.000 karakter. |
| `url` | string | HTTPS official-host. |
| `page_offered` | integer | Halaman pencarian saat kode dibuat. |

### 3.5 `PeriodOption`

| Field | Tipe | Aturan |
|---|---|---|
| `value` | string | Label yang dipilih user, misalnya `2024`. |
| `upstream_id` | string | ID periode resmi; tidak ditebak dari value. |
| `label` | string | Plain text untuk UI. |

### 3.6 `VerifiedRow`

| Field | Tipe | Aturan |
|---|---|---|
| `row_ref` | string | Prefix `row_`; server-generated. |
| `search_id` | string | Harus frame aktif saat row dibuat. |
| `candidate_code` | string | Kandidat `S#`/`T#`; `P#` dilarang. |
| `source_family` | enum | Hanya `simdasi|dynamic`. |
| `source_identifier` | string | Cocok Candidate. |
| `indicator_id` | string | ID resmi atau normalized title bila API tidak memberi ID; keputusan parser terdokumentasi. |
| `indicator` | string | Plain text non-kosong. |
| `value_decimal` | string | Canonical decimal: regex `^-?[0-9]+(?:\.[0-9]+)?$`. |
| `display_value` | string | Format resmi Indonesia yang disajikan. |
| `unit` | string | Non-kosong dan terverifikasi. |
| `period` | string | Cocok pilihan periode. |
| `coverage` | string | Nama wilayah/kategori cakupan. |
| `coverage_code` | string | Exact key pada registry `territories-1306.yaml`; `1306` untuk kabupaten atau kode turunan yang memiliki ancestor `1306`. |
| `source_title` | string | Non-kosong. |
| `source_type` | string | `Web API BPS - SIMDASI` atau `Web API BPS - Tabel Dinamis`. |
| `source_url` | string | HTTPS official-host. |
| `answerable` | boolean | Wajib true. |
| `metadata_complete` | boolean | Wajib true. |
| `metadata_missing` | list[string] | Wajib kosong. |

### 3.7 `DerivedResult`

| Field | Tipe | Aturan |
|---|---|---|
| `start_row_ref` | string | VerifiedRow comparable. |
| `end_row_ref` | string | VerifiedRow comparable. |
| `difference_decimal` | string | Exact Decimal canonical. |
| `difference_display` | string | Format Indonesia. |
| `percent_decimal` | string|null | Null hanya jika baseline nol atau operasi selisih saja. |
| `percent_display` | string|null | Dua desimal `ROUND_HALF_UP`. |
| `direction` | enum | `naik`, `turun`, `tetap`. |
| `formula` | string | Template deterministik, bukan teks LLM bebas. |

## 4. BrowserState `localStorage`

Key tunggal: `marawa.prototype.v1`.

| Field | Tipe | Aturan |
|---|---|---|
| `schema_version` | integer | Tepat 1; nilai lain dihapus setelah konfirmasi user. |
| `session_id` | string | Session aktif. |
| `server_generation` | string | Generasi saat sesi dibuat. |
| `state_version` | integer | Versi terakhir dari server. |
| `transcript` | list[`Bubble`] | Maksimum 100; FIFO. |

`Bubble` memiliki field tertutup: `id`, `role=user|assistant|system`, `text`, `actions`, `created_at`, `delivery_state=pending|sent|failed`. `actions` adalah list `{id,label,value,kind=candidate|period|next|confirm|handover|guestbook}`. Browser merender `text` dengan `textContent`.

## 5. Running example state

```json
{
  "session_id": "pv1_k7R3mQ8vN2xP5tY9aB4cD6fH",
  "server_generation": "boot_Jul21A",
  "state_version": 4,
  "created_at": "2026-07-21T02:00:00Z",
  "last_active_at": "2026-07-21T02:04:00Z",
  "messages": [
    {
      "role": "user",
      "content": "data jumlah penduduk Padang Pariaman",
      "message_id": "0f3d31b0-b204-4ed8-bb85-dac9acae8f27",
      "created_at": "2026-07-21T02:00:05Z",
      "provenance_refs": []
    },
    {
      "role": "user",
      "content": "S1",
      "message_id": "89781679-25f6-4f30-a6d6-a72a5dbe2db8",
      "created_at": "2026-07-21T02:01:00Z",
      "provenance_refs": []
    },
    {
      "role": "user",
      "content": "2024",
      "message_id": "40805d90-11c9-4292-9237-c9ecadfaacb0",
      "created_at": "2026-07-21T02:02:00Z",
      "provenance_refs": []
    }
  ],
  "frame": {
    "search_id": "search_penduduk_01",
    "query": "data jumlah penduduk Padang Pariaman",
    "canonical_query": "data jumlah penduduk padang pariaman",
    "page": 1,
    "next_numbers": {"S": 2, "T": 2, "P": 2},
    "candidates": {
      "S1": {
        "code": "S1",
        "source_family": "simdasi",
        "source_identifier": "tb_penduduk_01",
        "title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
        "subject": "Kependudukan",
        "periods": ["2024", "2023"],
        "abstract": null,
        "url": "https://padangpariamankab.bps.go.id/id/statistics-table",
        "page_offered": 1
      }
    },
    "selected_code": "S1",
    "period_page": 1,
    "offered_periods": [
      {"value": "2024", "upstream_id": "2024", "label": "2024"},
      {"value": "2023", "upstream_id": "2023", "label": "2023"}
    ],
    "selected_period": "2024",
    "verified_rows": {
      "row_penduduk_2024": {
        "row_ref": "row_penduduk_2024",
        "search_id": "search_penduduk_01",
        "candidate_code": "S1",
        "source_family": "simdasi",
        "source_identifier": "tb_penduduk_01",
        "indicator_id": "jumlah_penduduk",
        "indicator": "Jumlah Penduduk",
        "value_decimal": "434514",
        "display_value": "434.514",
        "unit": "jiwa",
        "period": "2024",
        "coverage": "Kabupaten Padang Pariaman",
        "coverage_code": "1306",
        "source_title": "Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan",
        "source_type": "Web API BPS - SIMDASI",
        "source_url": "https://padangpariamankab.bps.go.id/id/statistics-table",
        "answerable": true,
        "metadata_complete": true,
        "metadata_missing": []
      }
    },
    "active_row_refs": ["row_penduduk_2024"],
    "source_status": {"simdasi": "ok", "dynamic": "ok", "publication": "ok"}
  },
  "pending_topic": null,
  "response_cache": {}
}
```

Contoh sengaja hanya memuat kandidat yang dipakai running example; fixture acceptance mengisi tiga grup lengkap.

## 6. Aturan mutation dan concurrency

1. Semua mutation satu sesi berada dalam satu `asyncio.Lock`.
2. Request membawa `state_version`; mismatch menghasilkan 409 tanpa mutation.
3. `message_id` yang sudah ada mengembalikan TurnResponse cache dan tidak menaikkan versi.
4. Frame baru tidak dibuat sebelum konfirmasi topik baru selesai.
5. Menghapus sesi idempoten: sesi tidak ada tetap 204.
6. Sweeper menghapus sesi expired setiap 5 menit; request juga melakukan lazy expiry check.
7. Maksimum 100 sesi; sesi expired dibersihkan dulu, lalu sesi idle tertua ditolak/dihapus sesuai policy `session_capacity`.

## 7. Seeder/fixture development

Tidak ada seeder database. Development memakai fixture pada `tests/prototype_v1/fixtures/` dan dua berkas KB verified. Running example 2023/2024 harus tersedia sebagai fixture. Fixture wajib memiliki marker top-level `fixture=true` dan tidak boleh dimuat saat `APP_ENV` bukan `test`.

## 8. Tangga migrasi ke storage durable

Saat WhatsApp/handover nyata disetujui, state berikut wajib pindah ke PostgreSQL melalui paket desain baru: conversation, inbound/outbound message, frame kandidat, verified rows, handover session, ownership generation, timeout deadline, account, setting, dan audit. **Tidak ada skema production yang boleh diturunkan otomatis dari object prototype ini.**
