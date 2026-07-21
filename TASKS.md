# TASKS.md — Rencana Implementasi Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> Kerjakan berurutan dengan TDD: test gagal karena behavior belum ada → kode minimum → test hijau.
> Estimasi: 4–6 minggu untuk 1 developer. Checkbox hanya dicentang setelah bukti benar-benar dijalankan.

## Aturan eksekusi

1. Source baru hanya di `prototype_v1/`; test baru hanya di `tests/prototype_v1/`.
2. Jangan mengubah jalur WhatsApp/dashboard production kecuali task menyebut path itu secara eksplisit; paket ini tidak memiliki task tersebut.
3. Setiap task non-trivial mulai dengan test yang gagal karena behavior belum ada.
4. Satu commit/PR mencakup satu task atau dua task yang tidak dapat dipisah secara teknis.
5. Nilai fixture wajib ber-marker `fixture=true` dan tidak boleh tersedia saat `APP_ENV!=test`.
6. Verifikasi milestone menggunakan command yang tertulis; hasil aktual dicatat di checklist/PR.

## Milestone 0 — Isolasi dan kontrak aplikasi (Minggu 1)

- [x] **0.1 [A1] Package, dependency, dan health.** Buat `requirements.txt`, `requirements-dev.txt`, `prototype_v1/__init__.py`, `prototype_v1/app.py`, `prototype_v1/config.py`, `.env.prototype.example`, dan `tests/prototype_v1/test_app.py`. Dependency runtime hanya FastAPI, Uvicorn, httpx, openai, python-dotenv, dan PyYAML; dev hanya pytest/ruff. RED: import/`GET /api/prototype/live` gagal dan non-loopback/origin silang diterima. GREEN: app boot hanya loopback, response persis API-SPEC §2.1, cross-site mutating request 403, security headers lengkap, dan `APP_ENV=production` ditolak. **Bukti:** venv baru dapat meng-install requirements dan `python3 -m pytest tests/prototype_v1/test_app.py -q` hijau.
- [x] **0.2 [A1/A3] Static shell minimal.** Buat `prototype_v1/static/index.html`, `app.js`, `styles.css`; mount hanya pada app prototype. RED: contract test mencari form, transcript, reset, status, dan ARIA hooks lalu gagal. GREEN: shell dapat dibuka tanpa build step; belum memanggil LLM. **Bukti:** test contract hijau dan browser console tanpa error.
- [x] **0.3 [G1/G5] Config fail-fast.** Tulis validator URL/provider/BPS key, identity closed fields, domain constant literal `1306`, input/output limits, allowlist. RED: env invalid diterima. GREEN: setiap invalid case menolak startup tanpa mencetak secret. **Bukti:** `test_config.py` hijau.
- [x] **0.4 [A–H] Fixture boundary.** Buat folder fixture sesuai ARCHITECTURE §8 dan loader test-only. RED: fixture dapat dimuat di development. GREEN: hanya `APP_ENV=test` + `fixture=true` diterima. **Bukti:** `test_fixture_boundary.py` hijau.

## Milestone 1 — Sesi dan web chat lokal (Minggu 1–2) [A]

- [x] **1.1 [A2/A4] SessionStore in-memory.** Buat `prototype_v1/models.py`, `state.py`, test create/get/expiry/generation/capacity sesuai DATABASE §3/§6. RED: create/expiry test gagal. GREEN: opaque session, generation boot, idle 2 jam, maksimum 100 sesi. **Bukti:** `test_sessions.py` hijau termasuk SC-010.
- [x] **1.2 [A1/A2] Endpoint turn idempoten dan versioned.** Implement API-SPEC §3 skeleton dengan echo deterministic; lock per sesi, `message_id` cache, `state_version` conflict. RED: double submit menaikkan versi dua kali. GREEN: response kedua identik dan versi naik sekali. **Bukti:** `test_sessions.py -k 'idempotent or version'` hijau.
- [x] **1.3 [A2/A4] localStorage lifecycle.** Implement BrowserState schema v1, hydration, validation generation, maximum 100 bubble, pending/sent/failed. RED: refresh menghapus transcript dan restart mengaktifkan state lama. GREEN: SC-008/SC-010 lulus. **Bukti:** browser test/contract check `test_browser_contract.py` hijau.
- [x] **1.4 [A3] Reset idempoten.** Implement confirmation, DELETE, local cleanup, dan state visual baru. RED: cancel ikut menghapus atau delete ganda error. GREEN: cancel mempertahankan state; confirm/delete ganda aman. **Bukti:** SC-009 hijau.
- [x] **1.5 [A1] Responsive/accessibility pass.** CSS `100dvh`, 360×640, touch 44 px, focus visible, `aria-live`, no horizontal overflow. RED: contract tokens/attributes belum ada. GREEN: contract hijau lalu inspeksi browser desktop + mobile. **Bukti:** screenshot dan console output dicatat; SC-076 juga lulus.

## Milestone 2 — Guardrail dan loop agent (Minggu 2–3) [B/G] ← inti risiko

- [x] **2.1 [G1/G2/G3/G4] Provenance models, registry wilayah, dan gate.** Buat `prototype_v1/guardrails.py`, `scope.py`, dan schema `knowledge/territories-1306.yaml`; test domain injection/reject supplied domain, exact registry+ancestor check, tipe `verified/derived/sourced_knowledge/quoted_user/structural`, publication exclusion, metadata completeness. RED: observasi data tanpa row, angka knowledge tanpa source ref, atau coverage bermodal prefix/substring lolos. GREEN: SC-039–SC-040, SC-067–SC-070, dan SC-074 lulus. **Bukti:** `test_guardrails.py -q` hijau. Isi registry resmi/signoff PIC dikerjakan task 4.2.
- [x] **2.2 [G5] Sanitasi input/output/URL.** NFKC, control removal, HTML/script strip, official HTTPS host validation, no traceback/secret. RED: fixture script/evil URL lolos. GREEN: SC-075–SC-079 lulus. **Bukti:** test security parameterized hijau.
- [x] **2.3 [B1/B2] Intent dan clarification contract.** Buat intent enum/context builder dan provider mock; test greeting, vague data, mixed request, out-of-scope. RED: vague request melakukan search. GREEN: SC-001–SC-004 dan scope route lulus. **Bukti:** `test_agent_intents.py` hijau.
- [x] **2.4 [B3] Tool registry dan ordered dispatch.** Buat `tool_registry.py` dengan schema API-SPEC §4, strict args, context injection, unknown/additional/domain rejection. RED: tool invalid dieksekusi. GREEN: function spy membuktikan tidak dieksekusi. **Bukti:** `test_tool_registry.py` hijau.
- [x] **2.5 [B3/G5] Native agent loop budget.** Buat `agent_loop.py`; RED: mock model loop selamanya. GREEN: hard max 6/10/2/120, serial tools, typed fallback; SC-080 lulus. **Bukti:** `test_agent_loop.py` hijau.
- [x] **2.6 [B4/B5] Frame dan pergantian topik.** Implement single SearchFrame, pending topic confirm/cancel, reset codes. RED: topik baru menimpa frame tanpa konfirmasi. GREEN: SC-005–SC-007 dan SC-024 lulus. **Bukti:** `test_state.py` hijau.
- [x] **2.7 [G5] Templates deterministik.** Buat `templates.py` persis AGENT §7; golden tests untuk seluruh template dan action. RED: template/URL bebas dari model. GREEN: exact template + official action. **Bukti:** `test_templates.py` hijau.

## Milestone 3 — Kandidat, periode, data, dan publikasi (Minggu 3–4) [C/D]

- [x] **3.1 [C1/C2/C3] Adapter search tiga katalog.** Buat `bps_adapter.py` dan `catalog_service.py` dari kontrak Web API BPS terverifikasi; gunakan satu `httpx.AsyncClient` dan cache in-memory ARCHITECTURE §6. Jangan import atau copy project lain. RED: parser fixtures gagal/partial failure membatalkan semua. GREEN: normalized family result dan SC-011/SC-014–SC-016 lulus. **Bukti:** `test_catalogs.py` hijau.
- [x] **3.2 [C4/C5] Stable numbering, dedupe, pagination.** RED: page 2 me-reset S1 atau duplikat mengambil kode. GREEN: 3/source/page, S4/T4/P4, stable map maksimum 54. **Bukti:** SC-012–SC-013 dan SC-017–SC-022 lulus.
- [x] **3.3 [C6] Candidate resolver gate.** Implement explicit code + exact-unique normalized title, singleton no auto-select, stale code rejection. RED: S99/singleton fetch lolos. GREEN: SC-023–SC-024 lulus. **Bukti:** test spy membuktikan fetch count 0 pada invalid selection.
- [x] **3.4 [D1/D2] Period discovery/gate.** SIMDASI periods dari candidate, Dynamic model `th`, 20/page dan maksimum 10 page, stable accumulated offered-period state. RED: latest auto-selected, page invalid, halaman baru menghapus periode lama, atau 2022 arbitrary fetch. GREEN: SC-025–SC-030 lulus. **Bukti:** `test_periods.py` hijau.
- [x] **3.5 [D3/G4] SIMDASI detail parser.** Implement parser dari kontrak endpoint/fixture resmi yang tersimpan di repository ini; jangan import atau copy `bps_client.py`/SQLModel dari project lain. RED: malformed/unit/domain fixtures lolos. GREEN: SC-031/SC-033–SC-036 lulus untuk SIMDASI. **Bukti:** `test_fetch_and_provenance.py -k simdasi` hijau.
- [x] **3.6 [D3/G4] Dynamic data parser.** Implement metadata pagination, dimensions, datacontent, domain rows, Decimal canonical. RED: key parsing/foreign coverage salah. GREEN: SC-032 dan metadata parameterized lulus. **Bukti:** `test_fetch_and_provenance.py -k dynamic` hijau.
- [x] **3.7 [D4] Deterministic data renderer.** Render delapan unsur, maksimum 10 row/bubble, total/truncated, Indonesian display exact. RED: LLM dapat mengubah angka/judul. GREEN: renderer golden tests dan SC-031–SC-036 lulus. **Bukti:** snapshot text exact hijau.
- [x] **3.8 [D5/G3] Publication renderer.** Metadata only, abstract empty template, no active rows/number whitelist. RED: P1 memanggil period/fetch atau membuat verified row. GREEN: SC-027/SC-037–SC-038 lulus. **Bukti:** spy call count dan state assertion hijau.

## Milestone 4 — Pengetahuan dan analisis (Minggu 4–5) [E/F]

- [x] **4.1 [E1] Glosarium parser + graceful failure.** Implement documented model/fields dengan fixture resmi; HTTP 500 menjadi `glossary_unavailable`, tidak di-cache. RED: 500 melempar/raw body atau model fallback. GREEN: SC-039/SC-043/SC-078/SC-079 lulus. **Bukti:** `test_knowledge.py -k glossary` hijau.
- [x] **4.2 [E2/E3/G1] Verified KB dan registry wilayah.** Loader verified-only, lexical ranking max 4, exact territory code+ancestor, serta seed konten sementara untuk demo. **Bukti:** `test_knowledge.py -k 'kb or territory'` hijau. **Debt:** seed diberi label belum signoff PIC/MFD dan wajib diganti sebelum produksi.
- [x] **4.3 [E4/E5] Conflict/no-match renderer.** RED: dua definisi dilebur atau no-match dijawab LLM. GREEN: source blocks terpisah, conflict admin action, exact no-source template; SC-041–SC-044 lulus. **Bukti:** golden tests hijau.
- [x] **4.4 [F1] Follow-up period/dimension resolver.** RED: follow-up mengulang catalog atau memilih dimension ambigu. GREEN: SC-045–SC-047 lulus. **Bukti:** tool call trace mock menunjukkan no search ulang.
- [x] **4.5 [F2/F3] Comparable + selisih Decimal.** Buat `analysis.py`; RED: beda indicator/unit/coverage tetap dihitung. GREEN: exact Decimal difference dan reason enum; SC-048/SC-053–SC-056 lulus. **Bukti:** `test_analysis.py` hijau.
- [x] **4.6 [F4/F5] Persen/pembulatan/arah.** RED: float drift, baseline 0, arah dibuat model. GREEN: ROUND_HALF_UP 2 desimal, zero_baseline, direction from sign; SC-049–SC-052/SC-057 lulus. **Bukti:** `test_analysis.py` hijau.
- [x] **4.7 [F1–F5] Analysis renderer + provenance.** RED: jawaban tidak punya rumus/source atau menambah angka. GREEN: SC-058 exact invariant lulus. **Bukti:** output gate whitelist sama dengan verified + derived tokens.

## Milestone 5 — Handover mock dan integrasi vertikal (Minggu 5) [H]

- [x] **5.1 [H1/H2] Mock handover state/actions.** Implement tool enum empat action dan template transparan. RED: response menyiratkan petugas nyata sedang terhubung. GREEN: SC-059–SC-065 lulus. **Bukti:** `test_handover_mock.py` hijau.
- [x] **5.2 [H3] Buku Tamu official URL.** RED: arbitrary/short URL diterima. GREEN: identity URL exact + allowlist; SC-066 lulus. **Bukti:** test config/renderer hijau.
- [x] **5.3 [A–H] Running example end-to-end.** Hubungkan UI → REST → loop mock → search → S1 → period → data → compare. RED: test journey gagal pada fitur belum terhubung. GREEN: API response sama dengan API-SPEC §3.2–§3.5. **Bukti:** `test_running_example.py -q` hijau.
- [x] **5.4 [A–H] Partial failure journey.** Glosarium 500, Publication timeout, malformed Dynamic, LLM retry, admin fallback. GREEN berarti fallback jujur, bukan data muncul. **Bukti:** acceptance subset SC-015/SC-016/SC-043/SC-078–SC-080 hijau.

## Milestone 6 — Gate 80, live smoke, dan review (Minggu 6)

- [x] **6.1 [A–H] Acceptance harness SC-001–SC-080.** Buat `test_acceptance_80.py`; setiap ID muncul tepat satu test marker. **Bukti:** script inventory menghasilkan count 80, tidak ada ID hilang/duplikat.
- [x] **6.2 [G] Security review.** Jalankan ARCHITECTURE §10; test prompt/identity/disclosure/tool abuse/source injection/XSS/URL/secret. **Bukti:** SC-071–SC-080 hijau dan scan response/log tidak menemukan value secret.
- [x] **6.3 [A] Browser UAT nyata.** Serve app prototype, cek desktop dan 360×640 via browser: greeting, search, refresh, reset, expired, loading/error, keyboard/focus. **Bukti:** screenshot desktop/mobile + console tanpa error; jangan klaim responsive tanpa ini.
- [ ] **6.4 [C/D/E] Live smoke Web API BPS.** Jalankan satu query nyata per SIMDASI, Dynamic, Publication, Glosarium dengan key; simpan hanya status/schema tersanitasi, bukan key/raw secret. **Gate:** keempatnya minimal satu sukses. Jika Glosarium masih 500, Prototype dapat didemokan fallback tetapi **belum direkomendasikan ke fase 2** (DECISIONS #18).
- [x] **6.5 [B] Provider conformance.** Jalankan 80 fixture pada model production candidate. **Bukti:** 80/80; tool schema/calls valid; no unsupported vendor feature.
- [x] **6.6 [A–H] Spec compliance review.** Review FEATURES→PRD→API/DB/AGENT→tests; perbaiki blocker/critical. **Bukti:** consistency script dan manual checklist README hijau.
- [x] **6.7 [A–H] Code quality/final gate.** `python3 -m pytest tests/prototype_v1 -q`, `ruff check prototype_v1 tests/prototype_v1`, `git diff --check`; review diff agar tidak menyentuh production path di luar izin. **Bukti:** seluruh command exit 0.
- [x] **6.8 [PO] UAT keputusan.** PO memutuskan lanjut fase WhatsApp/dashboard dengan Glosarium live dan 9router sebagai accepted degraded dependency sementara (DECISIONS #24). Automated UAT wajib tetap hijau; belum ada deploy production.

## Pemetaan sub-fitur ke task

| Modul | Task |
|---|---|
| A1–A4 | 0.1–0.2, 1.1–1.5 |
| B1–B5 | 2.3–2.6 |
| C1–C6 | 3.1–3.3 |
| D1–D5 | 3.4–3.8 |
| E1–E5 | 4.1–4.3 |
| F1–F5 | 4.4–4.7 |
| G1–G5 | 0.3, 2.1–2.2, 2.5, 3.5–3.8, 6.2 |
| H1–H3 | 5.1–5.2 |

## Pertanyaan Product Owner

| # | Pertanyaan | Status/keputusan |
|---|---|---|
| 1 | Siapa nama/jabatan PIC PST yang memverifikasi KB Prototype 1 serta registry MFD kecamatan/nagari domain 1306, dan tanggal verifikasinya? | **SEED SEMENTARA DIIZINKAN PO.** Tidak memblokir demo, tetapi belum merupakan signoff resmi dan tetap memblokir klaim produksi. |
| 2 | Model/provider mana yang menjadi kandidat UAT? | **SUDAH TERJAWAB:** Gemini native adalah provider utama; 9router accepted unavailable sementara (DECISIONS #24). |
| 3 | Apakah Glosarium Web API BPS sudah kembali sukses saat UAT? | **BELUM TERJAWAB karena time-sensitive.** Smoke 21 Jul 2026 menghasilkan HTTP 500; cek ulang task 6.4. |
| 4 | Apakah empat smoke live wajib sebelum fase WhatsApp? | **DISUPERSEDE — DECISIONS #24:** Glosarium live diterima degraded sementara; fallback KB wajib dan kegagalan tetap terlihat. |
| 5 | Lokasi source prototype? | **SUDAH TERJAWAB — DECISIONS #20:** repository mandiri `/home/ubuntu/projects/marawa-agentic`, package `prototype_v1/`. |
