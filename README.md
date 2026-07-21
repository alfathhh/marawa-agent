# Marawa Prototype 1 — Dokumentasi Proyek

> Indeks versi 1.0 · 21 Juli 2026

Repository mandiri Marawa Agentic untuk membuktikan pencarian data resmi BPS domain `1306`, pengetahuan terverifikasi, dan analisis deterministik melalui web chat lokal. Prototype telah diimplementasikan dan lulus contract test; belum ada deployment production.

## Mulai dari mana

1. **FEATURES.md** — outcome, batas, modul A–H, dan roadmap non-kontrak.
2. **PRD.md** — masalah, role, aturan bisnis, user flow, out of scope, DoD.
3. **DECISIONS.md** — keputusan PO mengikat dan risiko yang diterima.
4. **ARCHITECTURE.md** — stack minimum, diagram, state, adapter BPS, failure strategy.
5. **DATABASE.md** — keputusan tanpa database dan kontrak object in-memory/browser.
6. **API-SPEC.md** — REST browser serta schema/error tool internal.
7. **AGENT.md** — persona, system prompt, tools, source hierarchy, state, templates.
8. **TEST-SCENARIOS.md** — 80 skenario gate normatif.
9. **TASKS.md** — urutan TDD M0–M6 dan pertanyaan PO.
10. **AGENTS.md** — aturan coding agent/developer.

## Lima konsep kunci

1. **LLM bukan sumber fakta** — PRD §4.2, AGENT §5.
2. **Pengguna memilih kandidat dan periode** — PRD §5.C–D.
3. **Domain angka dikunci ke `1306` runtime-only** — PRD §4.1, ARCHITECTURE §4.
4. **State sengaja tidak durable** — DATABASE §1; restart mengakhiri sesi.
5. **Lulus berarti 80/80 + smoke live** — PRD §9, TEST-SCENARIOS §4, TASKS M6.

## Alur utama

```text
web chat → search SIMDASI + Dynamic + Publication
→ user pilih S#/T#/P#
→ S/T: user pilih periode → verified rows → jawaban/provenance
→ follow-up/Decimal analysis
→ no source/tidak tuntas → admin mock → Buku Tamu
```

## Status sumber eksternal per 21 Juli 2026

| Sumber | Kontrak | Status live yang terverifikasi saat docs dibuat |
|---|---|---|
| SIMDASI | Interoperabilitas service ID 23, MFD `1306000` | Live sukses: HTTP 200/OK, katalog query `penduduk` menghasilkan kandidat |
| Tabel Dinamis | Web API BPS resmi | Live sukses: HTTP 200/OK |
| Publikasi | Web API BPS resmi | Live sukses: HTTP 200/OK |
| Glosarium | List + detail sesuai URL yang dibentuk UI dokumentasi | Live gagal: HTTP 500 `Please re-check your URL Request`; fallback KB aktif |
| SIRuSa | Portal resmi tersedia | API resmi belum terverifikasi; out of scope, tanpa scraper |
| KB PST | File lokal verified-only | Seed demo sementara aktif; signoff PIC/MFD resmi tetap debt produksi |

Shortlink Buku Tamu `https://s.bps.go.id/tamu1306` diverifikasi melalui request HEAD pada 21 Juli 2026: HTTP 200 dan mengarah ke Google Forms. Backend hanya menampilkan shortlink BPS tersebut dan tidak mengikuti redirect server-side.

Status ini time-sensitive. TASKS 6.4 wajib menguji ulang tanpa memaparkan credential.

## Status dokumen

| File | Versi | Status |
|---|---:|---|
| FEATURES.md | 1.0 | Disetujui/generate awal |
| PRD.md | 1.0 | Disetujui/generate awal |
| ARCHITECTURE.md | 1.0 | Disetujui/generate awal |
| DATABASE.md | 1.0 | Disetujui/generate awal |
| API-SPEC.md | 1.0 | Disetujui/generate awal |
| AGENT.md | 1.0 | Disetujui/generate awal |
| TEST-SCENARIOS.md | 1.0 | 80 skenario normatif |
| TASKS.md | 1.0 | Direncanakan; belum dieksekusi |
| DECISIONS.md | 1.0 | Append-only |
| AGENTS.md | 1.0 | Aturan implementasi |
| README.md | 1.0 | Indeks |

## Consistency gate sebelum coding

- [x] Semua 38 ID FEATURES A1–H3 muncul di PRD dan TASKS mapping.
- [x] REST/tool schema cocok dengan DATABASE object contract.
- [x] Error code API-SPEC tertutup dan dipakai AGENT/TASKS.
- [x] 80 ID SC unik, berurutan, dan punya Given/When/Then.
- [x] Tidak ada aturan yang menjadikan Publikasi sumber angka.
- [x] Tidak ada SIRuSa scraper/API asumsi.
- [x] Tidak ada database/deployment/WhatsApp/dashboard terselundup ke task Prototype 1.
- [x] Running example konsisten: Rina, `pv1_k7R3mQ8vN2xP5tY9aB4cD6fH`, S1, 2023=430.000, 2024=434.514, difference 4.514, percent 1,05%.
- [x] Pertanyaan PIC/provider/Glosarium tercatat di TASKS.

Audit lokal terakhir: 11 file, 38 ID fitur unik, 80 skenario unik, 80 Given/When/Then, 29 blok JSON valid, seluruh code fence seimbang, seluruh referensi dokumen tersedia, dan `git diff --check` bersih.
