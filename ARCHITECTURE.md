# ARCHITECTURE.md — Arsitektur Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> Baca PRD.md lebih dulu. Dokumen ini menjawab bagaimana Prototype 1 dibangun dengan perubahan minimum.

## 1. Tech stack

| Lapisan | Pilihan | Alasan | Alternatif ditolak |
|---|---|---|---|
| Runtime | Python 3.12+ | Host aktif memakai 3.12; tidak perlu runtime baru. | Python 3.13 wajib ditolak untuk prototype karena bukan kebutuhan perilaku. |
| HTTP | FastAPI 0.x + Uvicorn | Dependency langsung minimum untuk validasi, REST, dan static serving. | Flask tidak memberi keuntungan; Django/Next.js terlalu besar. |
| LLM | SDK `openai` 2.x, Chat Completions OpenAI-compatible | Provider dapat diganti via env dan tool calling sudah tersedia. | SDK vendor, LangChain, dan LlamaIndex menyembunyikan gate dan menambah abstraksi. |
| HTTP eksternal | `httpx` 0.28 | Dependency langsung minimum; timeout dan async client jelas. | `requests` menduplikasi HTTP client; browser scraping tidak dibutuhkan. |
| Frontend | HTML, CSS, vanilla JavaScript | Satu layar chat; native platform cukup. | React/Vue/Svelte menambah build chain tanpa kebutuhan. |
| State | Dict in-memory server + `localStorage` browser | Satu user lokal; restart boleh mengakhiri sesi. | SQLite/PostgreSQL/Redis tidak memberi nilai untuk acceptance Prototype 1. |
| KB | YAML/Markdown terverifikasi, dimuat in-memory | Korpus kecil dan operator-readable. | Vector DB/embedding ditunda sampai recall lexical terbukti tidak cukup. |
| Hitung | `decimal.Decimal` stdlib | Presisi dan aturan pembulatan deterministik. | Float dan aritmetika LLM tidak aman. |
| Test | pytest + fixture JSON | Sudah dependency; kontrak eksternal reproducible. | Test live-only rapuh terhadap perubahan upstream. |
| Deployment | Lokal, satu proses Uvicorn | Sesuai scope prototype. | Docker/production proxy/multi-worker di luar scope. |

Versi exact dideklarasikan di `requirements.txt` dan `requirements-dev.txt` saat TASKS 0.1; bump mayor memerlukan keputusan baru.

## 2. Diagram arsitektur

```text
Browser lokal
  ├─ static/index.html + app.js + styles.css
  ├─ transcript/session metadata → localStorage
  └─ REST /api/prototype/*
             │
             ▼
FastAPI prototype_v1/app.py (single process)
  ├─ SessionStore in-memory ─ frame kandidat/periode/data aktif
  ├─ agent_loop.py ─ OpenAI-compatible tool loop
  ├─ guardrails.py ─ domain/provenance/output gate
  ├─ catalog_service.py
  │    └─ bps_adapter.py ─ SIMDASI/Dynamic/Publication/Glosarium
  ├─ knowledge.py ─ verified YAML/Markdown
  └─ analysis.py ─ Decimal compare
             │
             ├─ HTTPS → Web API BPS
             └─ HTTPS → provider LLM
```

Tidak ada jalur dari Prototype 1 ke Evolution API, dashboard production, database production, atau fungsi handover existing.

## 3. Request dan state lifecycle

1. Browser `POST /sessions`; server menghasilkan `session_id` opaque 128-bit dan mengembalikan `server_generation` acak per boot.
2. Browser mengirim `message_id` UUID, `text`, dan `state_version` terakhir.
3. Server memegang lock per sesi, menolak versi basi, dan mengembalikan cache respons jika `message_id` duplikat.
4. Input gate berjalan sebelum LLM.
5. Agent loop memanggil tool melalui registry dan gate.
6. Output gate memvalidasi provenance, URL, dan markup sebelum response.
7. State version naik tepat satu setelah turn tersimpan in-memory.
8. Session sweeper menghapus sesi idle > 2 jam; reset menghapus segera.

`localStorage` hanya menyimpan transcript tampilan. Setelah restart, `server_generation` berubah dan transcript tidak boleh dipakai untuk merekonstruksi kandidat/data aktif.

## 4. Agent loop dan tool gate

Urutan dispatch wajib:

```text
registered tool
→ strict JSON schema
→ reject additional property/domain
→ inject domain='1306' untuk tool BPS
→ session/frame/state_version valid
→ candidate offered and source-compatible
→ period offered (untuk fetch)
→ execute
→ normalize result
→ register provenance/row_ref
```

Budget per turn: 6 model request, 10 execution, 2 canonical call identik, deadline 120 detik. Multi-tool dijalankan serial; parallel dinonaktifkan agar mutation frame deterministik.

Kandidat dan periode di-resolve runtime. Model boleh mengusulkan `S1` atau `2024`; runtime yang menentukan apakah sah.

## 5. Provenance dan output

### 5.1 Row terverifikasi

Satu row angka baru terdaftar bila seluruh field berikut valid:

- `row_ref` server-generated;
- `source_family`: `simdasi` atau `dynamic`;
- `source_identifier` cocok kandidat aktif;
- `indicator_id`/title non-kosong;
- `value_decimal` dapat diparse sebagai Decimal;
- `display_value`, `unit`, `period`, `coverage`, `coverage_code` non-kosong;
- `coverage_code` sama dengan domain `1306` atau turunan resmi;
- `source_title`, `source_type`, `source_url` HTTPS official-host;
- `answerable=true`, `metadata.complete=true`, `metadata.missing=[]`.

### 5.2 Whitelist angka

Output gate memakai token angka bertipe:

- `verified`: nilai tampilan dari row tool;
- `derived`: hasil analysis.py;
- `sourced_knowledge`: token yang terdapat pada definisi/prosedur Glosarium atau KB terverifikasi dan dirender dengan atribusi; tidak sah sebagai observasi indikator;
- `quoted_user`: hanya boleh muncul sebagai kutipan/kriteria;
- `structural`: kode kandidat, tahun yang sudah diverifikasi, nomor urut, dan URL.

Observasi data statistik hanya boleh memakai `verified`/`derived`. Definisi/prosedur boleh memakai `sourced_knowledge` dalam batas teks source ref yang dikembalikan tool. Bila render LLM gagal gate, backend memakai renderer deterministik dari object tool; jika renderer gagal, gunakan fallback tanpa angka/URL.

### 5.3 URL

Host allowlist tertutup:

- `bps.go.id` dan seluruh subdomain `*.bps.go.id`;
- `s.bps.go.id` untuk Buku Tamu.

Skema harus HTTPS. Backend tidak melakukan HEAD/GET atau mengikuti redirect untuk URL yang hanya ditampilkan; ini mencegah SSRF dan menjaga shortlink resmi tetap persis. Khusus Buku Tamu, hanya nilai exact `https://s.bps.go.id/tamu1306` dari identity config terverifikasi yang diterima. Browser pengguna yang mengikuti redirect setelah klik. Jika adapter memang harus mengikuti redirect untuk mengambil data, setiap hop dan host akhir wajib kembali berada pada allowlist BPS.

## 6. Adapter Web API BPS

Adapter memakai `BPS_API_BASE=https://webapi.bps.go.id/v1/api`, API key server-side, timeout connect 5 detik/read 20 detik, dan retry maksimal satu kali untuk timeout/429/5xx. 4xx selain 429 tidak di-retry.

| Keluarga | Kontrak | Cache in-memory |
|---|---|---:|
| SIMDASI list/detail | Endpoint interoperabilitas, MFD `1306000`, parser schema tervalidasi | list 1 jam; data 6 jam |
| Tabel Dinamis | model `var`, `th`, dimensi, `data` | metadata 1 jam; period 24 jam; data 6 jam |
| Publikasi | model `publication`; metadata saja | 1 jam |
| Glosarium | model `glosarium`; prefix/page/perpage sesuai docs resmi | 24 jam jika sukses; error tidak di-cache |

Cache key menghapus API key dan memasukkan keluarga/path parameter. Maksimum 256 entries LRU; restart mengosongkan cache.

### Status Glosarium

Dokumentasi resmi yang diekstrak 21 Juli 2026 menyebut:

- endpoint dasar `/v1/api/list`;
- model `glosarium`;
- parameter `prefix`, `page`, `perpage` (maksimum 500), `key`;
- field `_source.konsep`, `definisi`, `judulIndikator`, `satuan`, `sumberKonten`, dan identifier.

Smoke request live pada tanggal yang sama untuk beberapa bentuk path/query menghasilkan HTTP 500 upstream (`Undefined property: stdClass::$hits`). Karena itu:

1. fixture kontrak resmi dipakai untuk implementasi/test;
2. live 500 dinormalisasi `glossary_unavailable`;
3. tidak ada fallback pengetahuan model;
4. minimal satu smoke live harus hijau sebelum rekomendasi naik ke fase WhatsApp.

## 7. Knowledge base dan SIRuSa

KB berada di `prototype_v1/knowledge/*.yaml`. Loader fail-fast bila metadata wajib hilang, `verified` bukan boolean, atau `source_url` yang non-null bukan official HTTPS. `source_url=null` boleh untuk dokumen internal yang memiliki `source_key`, `title`, `verified_by`, dan `verified_at`; atribusinya memakai judul dokumen, bukan URL buatan. Pencarian awal menggunakan normalisasi NFKC, casefold, token overlap, dan alias eksplisit per dokumen. Maksimum 4 chunk. Ini cukup untuk korpus kecil; jika 80 skenario menunjukkan recall kurang, barulah proposal retrieval lain dibuat.

Registry `territories-1306.yaml` bukan knowledge bebas: ia berisi daftar tertutup nama, alias, level, dan kode resmi Kabupaten Padang Pariaman/kecamatan/nagari yang telah diverifikasi dari MFD BPS. Runtime menerima sebuah coverage hanya bila kode exact ada di registry dan memiliki ancestor `1306`; kecocokan substring/prefix angka tanpa record registry dilarang. File wajib memiliki `source_url`, `verified_by`, dan `verified_at`. Sampai registry ditandatangani PIC, row kecamatan/nagari ditahan; row kabupaten exact `1306` tetap dapat diproses.

SIRuSa tidak dipanggil dan tidak di-scrape. Adapter baru hanya boleh dirancang setelah kontrak API resmi terverifikasi sesuai DECISIONS #14.

## 8. Struktur folder

```text
prototype_v1/
├── __init__.py
├── app.py                 # FastAPI routes + static files
├── config.py              # env + identity/allowlist validation
├── models.py              # request/response/dataclass contracts
├── state.py               # SessionStore, locks, expiry, idempotency
├── agent_loop.py          # OpenAI-compatible loop
├── tool_registry.py       # schemas + ordered dispatch gate
├── catalog_service.py     # candidate numbering/pagination/frame mutation
├── bps_adapter.py         # Web API BPS HTTP + parser/cache
├── knowledge.py           # verified KB retrieval
├── scope.py               # exact territory registry + domain gate
├── analysis.py            # Decimal comparable/difference/percent
├── guardrails.py          # input/output/provenance/URL gates
├── templates.py           # deterministic fallback renderers
├── knowledge/
│   ├── identity.yaml
│   ├── pst-services.yaml
│   └── territories-1306.yaml
└── static/
    ├── index.html
    ├── app.js
    └── styles.css

tests/prototype_v1/
├── fixtures/
│   ├── simdasi-search.json
│   ├── simdasi-data-2023.json
│   ├── simdasi-data-2024.json
│   ├── dynamic-search.json
│   ├── dynamic-data.json
│   ├── publication-search.json
│   └── glossary-list.json
├── test_sessions.py
├── test_catalogs.py
├── test_fetch_and_provenance.py
├── test_knowledge.py
├── test_analysis.py
├── test_guardrails.py
└── test_acceptance_80.py
```

Prototype memakai package `prototype_v1/` di repository mandiri ini. Tidak ada routing mount atau import dari project lain.

## 9. Konvensi error dan logging

Semua tool return object; tidak ada exception mentah ke loop. Error code tertutup di API-SPEC §8. Log berbentuk event JSON ke stdout: `event`, `session_suffix`, `tool`, `status`, `latency_ms`; tidak ada isi pesan, API key, prompt, full session ID, atau payload tool.

## 10. Security checklist

- [ ] API key hanya environment server dan tidak masuk URL log.
- [ ] `domain` absent dari tool schema dan supplied field ditolak.
- [ ] Strict schema `additionalProperties=false` untuk semua tool.
- [ ] Input/output di-limit 8.000/12.000 karakter.
- [ ] HTML/script dari API/KB di-strip sebelum model/UI.
- [ ] Frontend menggunakan `textContent`, bukan `innerHTML`, untuk konten sumber/user.
- [ ] URL output tidak di-fetch server; Buku Tamu hanya shortlink exact terverifikasi. Redirect adapter data, bila ada, divalidasi pada setiap hop dan host akhir.
- [ ] Session ID 128-bit, tidak sequential; state version mencegah race.
- [ ] Uvicorn bind default `127.0.0.1`; bind non-loopback ditolak pada Prototype 1.
- [ ] CORS hanya origin loopback exact terkonfigurasi; tidak memakai wildcard atau credential. Request mutating dengan `Origin` non-loopback atau `Sec-Fetch-Site: cross-site` ditolak 403 `origin_not_allowed`.
- [ ] Static response memasang CSP `default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`, `X-Frame-Options: DENY`, dan `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- [ ] Error response tidak memuat traceback, prompt, path secret, atau raw upstream body.
- [ ] Prompt injection/tool abuse/secret disclosure lulus TEST-SCENARIOS SC-071–SC-080.

## 11. Performance dan accessibility checklist

- [ ] Static first render < 1 detik pada mesin lokal.
- [ ] Endpoint sesi p95 < 300 ms lokal.
- [ ] Turn fast p95 < 3 detik; turn tool live p95 < 15 detik; deadline 120 detik.
- [ ] Maksimum 256 cache entries dan 100 sesi; sesi tertua/expired dibersihkan.
- [ ] Maksimum 3 kandidat per sumber dan 10 data rows per bubble.
- [ ] UI 360×640 dan desktop tanpa horizontal overflow.
- [ ] Input/button minimum 44×44 px; focus visible; label/aria-live tersedia.
- [ ] Loading, empty, partial-source-error, expired, dan offline state terlihat.

## 12. Tangga naik kompleksitas

- Tambah SQLite hanya jika sesi wajib tahan restart sebelum WhatsApp.
- Tambah retrieval embedding hanya jika fixture + UAT menunjukkan lexical KB gagal recall.
- Tambah PostgreSQL/durable queue hanya saat Evolution/dashboard masuk scope.
- Tambah frontend framework hanya jika dashboard multi-screen disetujui; bukan untuk chat Prototype 1.
