# DECISIONS.md — Log Keputusan Product Owner Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> Keputusan mengikat untuk Prototype 1. Perubahan wajib menjadi entri append-only baru.

| # | Tanggal | Keputusan | Dampak |
|---|---|---|---|
| 1 | Jul 2026 | **Prototype 1 adalah web chat lokal, bukan kanal WhatsApp.** Tujuannya membuktikan percakapan dan akurasi sebelum integrasi operasional. | FEATURES A–H · PRD §1/§8 · ARCHITECTURE §1–§2 |
| 2 | Jul 2026 | **Sumber Prototype 1: SIMDASI, Tabel Dinamis, Publikasi, Glosarium Web API BPS, dan KB PST terverifikasi.** | FEATURES C–E · PRD §4.2 · AGENT §4–§5 |
| 3 | Jul 2026 | **Setiap pencarian data menampilkan kandidat dari SIMDASI, Tabel Dinamis, dan Publikasi; pengguna selalu memilih.** Tidak ada auto-select, termasuk jika hanya satu kandidat. | FEATURES C · PRD §5.C · AGENT §6 |
| 4 | Jul 2026 | **Kode kandidat adalah `S#`, `T#`, `P#`.** Maksimal 3 per sumber per halaman; nomor berlanjut selama pencarian yang sama. | FEATURES C4–C5 · API-SPEC §4 |
| 5 | Jul 2026 | **`S#`/`T#` wajib diikuti pilihan periode eksplisit.** Periode terbaru tidak dipilih diam-diam. `P#` tidak memiliki tahap periode. | FEATURES D1–D2 · PRD §5.D |
| 6 | Jul 2026 | **Angka terkunci ke domain string `1306` dan turunannya.** Konsep statistik umum boleh bila punya sumber; angka luar wilayah ditolak. Domain tidak masuk schema LLM. | FEATURES G1 · PRD §4.1 · AGENT §4 |
| 7 | Jul 2026 | **LLM bukan sumber fakta.** Angka hanya dari baris Web API BPS terverifikasi; konsep dari Glosarium/KB; hasil turunan dari `Decimal`. No-match → jujur, admin, Buku Tamu. | PRD §4.2/§5.G · AGENT §1/§5 |
| 8 | Jul 2026 | **Publikasi hanya metadata.** Output tertutup: judul, abstraksi atau status tidak tersedia, dan URL resmi; publikasi tidak mengotorisasi angka. | FEATURES D5/G3 · PRD §5.D5 |
| 9 | Jul 2026 | **Analisis Prototype 1 mencakup follow-up periode/dimensi, selisih absolut, perubahan persen, dan arah naik/turun/tetap.** Perhitungan memakai `Decimal`; beda indikator/satuan/cakupan atau nilai awal nol untuk persen ditolak. | FEATURES F · PRD §5.F · AGENT §4 |
| 10 | Jul 2026 | **Handover hanya mock.** Desain final: pengguna tetap di nomor bot, admin membalas dari dashboard melalui nomor bot; implementasi relay ditunda. | FEATURES H/roadmap · PRD §5.H/§8 |
| 11 | Jul 2026 | **Semua layanan yang tidak tuntas memakai jalur admin → Buku Tamu.** Berlaku untuk data, perpustakaan, konsultasi, rekomendasi, definisi, dan layanan PST. | FEATURES H · PRD §5.H |
| 12 | Jul 2026 | **Satu sesi hanya punya satu pencarian aktif.** Topik baru harus dikonfirmasi; setelah setuju frame lama dibuang. | FEATURES B4–B5 · PRD §5.B |
| 13 | Jul 2026 | **Prototype tidak memakai database.** State server in-memory; browser menyimpan transcript. Refresh bertahan, restart server mengakhiri sesi. Risiko kehilangan sesi diketahui dan diterima karena ini prototype lokal. Mitigasi: UI mendeteksi generasi server dan meminta sesi baru. | DATABASE seluruhnya · ARCHITECTURE §3 |
| 14 | Jul 2026 | **SIRuSa ditunda sampai API resmi terverifikasi.** Tidak ada scraper pengganti. Syarat masuk: endpoint, autentikasi, pagination, schema, rate limit, dan stabilitas teruji. | PRD §8 · ARCHITECTURE §7 · TASKS Pertanyaan PO |
| 15 | Jul 2026 | **Jika dua sumber terverifikasi berbeda, tampilkan terpisah dengan konteks dan atribusi.** Pertentangan tidak diputus model; tawarkan admin. | FEATURES E4 · PRD §5.E |
| 16 | Jul 2026 | **Persona: Bahasa Indonesia ramah, ringkas, profesional; “Kak” paling banyak satu kali per bubble dan tidak wajib.** Marawa transparan sebagai asisten virtual dan tidak memakai tabel Markdown dalam bubble. | PRD §5.A · AGENT §1/§3 |
| 17 | Jul 2026 | **Gate kelulusan adalah 80 skenario wajib lulus.** Fixture deterministik menguji kontrak; smoke live eksternal terpisah dan kegagalan upstream harus menghasilkan fallback benar. | PRD §9 · AGENT §9 · TASKS M6 |
| 18 | 21 Jul 2026 | **Glosarium tetap fitur wajib, tetapi status live dicatat tidak terverifikasi bekerja.** Dokumentasi resmi memuat model `glosarium`, parameter, dan schema; smoke request beberapa bentuk resmi/umum menghasilkan HTTP 500 upstream. Risiko: E1 tidak dapat didemokan live saat upstream rusak. Mitigasi: contract fixture + graceful fallback; Prototype tidak dinyatakan siap fase berikutnya sebelum minimal satu smoke Glosarium live berhasil. | FEATURES E1 · ARCHITECTURE §7 · AGENT §4/§7 · TASKS M4/M6 |
| 19 | Jul 2026 | **Source code Prototype 1 terisolasi di `prototype_v1/` dan memakai dependency repo yang sudah ada.** Tidak memodifikasi jalur WhatsApp/dashboard production saat membuktikan prototype. | ARCHITECTURE §8 · TASKS M0–M6 |
| 20 | 21 Jul 2026 | **Marawa menjadi repository mandiri `/home/ubuntu/projects/marawa-agentic`.** Keputusan ini supersede bagian “memakai dependency repo yang sudah ada” pada #19. Dokumen berada di root repo; source tetap di package `prototype_v1/`; dependency dideklarasikan sendiri; import/copy dari `pst-fable-2` dilarang tanpa keputusan baru. | README · ARCHITECTURE §1/§8 · TASKS M0/M3 · AGENTS |
| 21 | 21 Jul 2026 | **PO mengizinkan seed KB sementara untuk demo, dengan label eksplisit belum signoff PIC/MFD.** Seed boleh melewati loader verified-only pada prototype, tetapi tidak boleh menjadi klaim produksi. | `prototype_v1/knowledge/` · TASKS M4.2 |
| 22 | 21 Jul 2026 | **SIMDASI domain 1306 memakai service interoperabilitas ID 23 dan MFD `1306000`.** Live smoke berhasil; endpoint list generik `model=simdasi` bukan kontrak katalog yang benar. | `bps_adapter.py` · TASKS M3/M6.4 |
| 23 | 21 Jul 2026 | **Glosarium diuji persis seperti URL yang dibentuk JavaScript dokumentasi.** List dan detail tetap HTTP 500 dengan pesan aplikasi `Please re-check your URL Request`; parser schema resmi `_source` tetap disiapkan dan fallback KB dipertahankan. | `bps_adapter.py` · TASKS M4.1/M6.4 |
| 24 | 21 Jul 2026 | **PO menerima Glosarium live dan 9router fallback sebagai degraded dependency sementara serta memutuskan lanjut ke fase operasional WhatsApp/dashboard.** Gemini tetap provider utama; fallback KB wajib saat Glosarium gagal; kegagalan 9router tidak boleh memblokir atau memicu jawaban tanpa sumber. | FASE-2.md · paket `operational/` |
| 25 | 21 Jul 2026 | **Status outbound WhatsApp tidak boleh dianggap delivered hanya karena Evolution `sendText` mengembalikan 2xx/provider ID.** Delivery final berasal dari webhook `messages.update`; status `ERROR` setelah provider menerima request wajib tercatat. | FASE-2.md · outbox/delivery contract |
| 26 | 21 Jul 2026 | **Persistence fase operasional memakai PostgreSQL 17, SQLAlchemy Core, Psycopg 3, dan Alembic.** Schema ditambah per milestone; tidak membuat seluruh dashboard/handover schema sebelum behavior-nya diuji. | `requirements-operational.txt` · `migrations/` · `operational/persistence.py` |
| 27 | 21 Jul 2026 | **Outbox berjalan single-worker/replica dengan PostgreSQL `FOR UPDATE SKIP LOCKED`, lease 90 detik, ordering per nomor, maksimal 8 attempt, dan exponential backoff maksimal 900 detik.** Multi-replica ditunda sampai seluruh fencing state diuji. | `operational/delivery.py` · migration `0002` |

## Konsekuensi teknis ringkas

1. `domain` tidak boleh muncul pada tool schema atau input browser.
2. Resolver kode kandidat berjalan di runtime sebelum LLM; model tidak berwenang memilih.
3. Data publication tidak pernah masuk whitelist angka.
4. `localStorage` bukan sumber state otoritatif; transcript hanya tampilan.
5. Tidak ada SQLModel, Alembic, Redis, vector DB, LangChain, atau LlamaIndex di source prototype.
6. Status Glosarium harus terlihat sebagai error sumber, bukan digantikan definisi model.
