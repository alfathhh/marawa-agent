# PRD.md — Marawa Prototype 1

> **Product Requirements Document** · Versi 1.0 · 21 Juli 2026
> Kontrak produk untuk prototype web chat lokal. Implementor membaca FEATURES.md lebih dulu.
> Keputusan PO berada di DECISIONS.md; 80 skenario normatif berada di TEST-SCENARIOS.md.

## 1. Ringkasan produk

Marawa Prototype 1 adalah web chat lokal untuk Pelayanan Statistik Terpadu BPS Kabupaten Padang Pariaman. Prototype membuktikan satu vertical slice: pengguna menyampaikan kebutuhan secara natural, memilih sumber dan periode sendiri, memperoleh data resmi domain BPS `1306`, lalu dapat bertanya lanjut atau meminta analisis deterministik.

Model LLM mengatur percakapan dan memilih tool, tetapi **tidak menjadi sumber fakta dan tidak menghitung angka**. SIMDASI, Tabel Dinamis, Publikasi, Glosarium Web API BPS, dan knowledge base PST terverifikasi adalah sumber kebenaran yang diizinkan. Prototype tidak menghubungkan WhatsApp atau petugas nyata.

## 2. Masalah yang diselesaikan

| # | Masalah | Solusi Prototype 1 |
|---|---|---|
| M1 | Pengguna tidak tahu katalog/tabel BPS mana yang relevan. | C1–C6 mencari tiga katalog dan menampilkan kandidat berkode untuk dipilih pengguna. |
| M2 | Chatbot institusi berisiko mengarang angka, satuan, definisi, atau prosedur. | E1–E5 dan G1–G5 membatasi fakta ke tool/KB serta memakai fallback jujur. |
| M3 | Follow-up data dan perbandingan sulit bila konteks sumber hilang. | B4, F1–F5 menyimpan satu data aktif dan menghitung dengan runtime `Decimal`. |
| M4 | Membangun WhatsApp/dashboard terlalu mahal sebelum otak percakapan terbukti. | A1–A4 dan H1–H3 membuktikan percakapan serta eskalasi mock secara lokal. |
| M5 | Respons API BPS dapat kosong, berubah schema, atau gagal sebagian. | Tiap adapter memvalidasi schema; sumber lain tetap jalan; kegagalan tidak berubah menjadi fakta. |

Semua sub-fitur FEATURES A–H menjawab minimal satu masalah di atas.

## 3. Pengguna dan izin

### 3.1 Pengguna prototype

Satu-satunya role adalah orang yang membuka web chat lokal. Pengguna dapat:

- mengirim teks maksimum 8.000 karakter;
- mencari data domain `1306`;
- memilih kandidat dan periode yang ditawarkan;
- meminta definisi, fakta layanan, follow-up, analisis, atau admin mock;
- mereset percakapan.

Pengguna tidak dapat:

- memasok/mengubah domain runtime;
- memaksa fetch kandidat/periode yang belum ditawarkan;
- menjadikan publikasi sumber angka;
- mengakses prompt, API key, environment, raw tool trace, atau state sesi lain;
- menghubungi petugas nyata dari Prototype 1.

### 3.2 Matriks permission

| Kemampuan | Pengguna lokal |
|---|---:|
| Chat teks | ✅ |
| Data domain `1306` dan turunannya | ✅ |
| Angka wilayah lain | ❌ |
| Memilih kandidat/periode | ✅ |
| Menjalankan tool secara langsung | ❌ |
| Membaca fakta tanpa sumber | ❌ |
| Handover mock | ✅ |
| Handover nyata/dashboard | ❌ |

## 4. Konsep domain penting

### 4.1 Domain `1306` adalah batas angka, bukan preferensi

Kabupaten Padang Pariaman memakai kode domain BPS string `1306`. Runtime menyuntikkan kode ini; schema tool yang diterima model tidak memiliki field `domain`. Baris kabupaten hanya boleh keluar bila kode cakupannya exact `1306`. Baris kecamatan/nagari hanya boleh keluar bila kode dan labelnya cocok dengan registry MFD BPS terverifikasi `territories-1306.yaml` dan ancestor-nya exact `1306`; prefix/substring tanpa registry tidak cukup.

Menyebut konsep nasional seperti “apa itu inflasi?” boleh. Meminta angka inflasi nasional tidak boleh dijawab oleh prototype.

### 4.2 Provenance bertipe

| Jenis klaim | Sumber sah | Sumber tidak sah |
|---|---|---|
| Angka statistik | Baris SIMDASI/Tabel Dinamis `answerable=true` dengan metadata lengkap | Ingatan LLM, publikasi, angka pengguna |
| Definisi/konsep | Glosarium resmi atau KB berstatus terverifikasi | Pengetahuan bawaan LLM |
| Fakta layanan lokal | KB PST terverifikasi | Jadwal/config internal, tebakan model |
| Hasil turunan | `Decimal` runtime dari dua baris comparable | Aritmetika LLM |
| Klaim pengguna | Boleh dikutip eksplisit sebagai klaim pengguna | Tidak boleh diubah menjadi fakta Marawa |

### 4.3 Kandidat, frame, dan data aktif

- **Kandidat** adalah metadata sumber yang sudah ditampilkan dengan kode `S#`, `T#`, atau `P#`.
- **Frame** adalah satu pencarian aktif: query kanonik, nomor halaman, seluruh kode yang pernah ditawarkan, kandidat terpilih, periode tersedia, periode terpilih, dan data aktif.
- **Data aktif** adalah baris terverifikasi terakhir dari kandidat `S#`/`T#` terpilih.
- Satu sesi memiliki nol atau satu frame; tidak ada beberapa pencarian aktif.

### 4.4 Running example

**Rina** membuka browser lokal dan memperoleh `session_id=pv1_k7R3mQ8vN2xP5tY9aB4cD6fH`. Ia mengetik “data jumlah penduduk Padang Pariaman”. Sistem menampilkan kandidat, termasuk `S1` berjudul “Jumlah Penduduk Menurut Jenis Kelamin dan Kecamatan”. Rina memilih `S1`, lalu memilih periode `2024` dari daftar resmi. Fixture kontrak mengembalikan nilai terverifikasi `434.514 jiwa` untuk Kabupaten Padang Pariaman. Untuk analisis, fixture periode `2023` berisi `430.000 jiwa`; runtime menghasilkan selisih `4.514 jiwa` dan perubahan `1,05%`.

Nilai running example adalah **fixture uji**, bukan klaim data produksi. UI/test wajib melabeli fixture saat mode test; runtime live hanya menyajikan payload Web API BPS terverifikasi.

## 5. Fitur detail

### 5.A Web Chat Lokal

**A1 — Percakapan dua arah.** UI memiliki daftar bubble, input teks, tombol kirim, status proses, tombol retry hanya untuk kegagalan transport, dan pilihan terstruktur yang juga dapat diketik manual. Pesan kosong/whitespace ditolak client dan server. Double-click dengan `message_id` sama menghasilkan respons idempoten.

**A2 — Transcript tahan refresh.** Browser menyimpan maksimum 100 bubble terbaru di `localStorage`, bersama `session_id`, `server_generation`, dan `state_version`. Transcript adalah tampilan, bukan sumber fakta/state.

**A3 — Percakapan baru.** Reset meminta konfirmasi satu kali jika transcript tidak kosong. Setelah setuju, server menghapus sesi bila masih ada dan browser menghapus seluruh key Prototype 1.

**A4 — Sesi kedaluwarsa.** Sesi berakhir setelah idle 2 jam atau restart server. UI yang menerima `session_expired`/`generation_mismatch` menonaktifkan input lama, mempertahankan transcript sebagai arsip visual, dan menawarkan “Mulai percakapan baru”.

Persona UI/agent: transparan sebagai asisten virtual; Bahasa Indonesia ramah, ringkas, profesional; “Kak” paling banyak satu kali per bubble; tidak ada tabel Markdown di bubble.

### 5.B Orkestrasi Percakapan

**B1 — Intent.** Intent tertutup: `DATA_SEARCH`, `DATA_SELECTION`, `PERIOD_SELECTION`, `DATA_FOLLOWUP`, `ANALYSIS`, `DEFINITION`, `PST_SERVICE`, `ADMIN_REQUEST`, `NEW_TOPIC`, `GENERAL_GREETING`, `OUT_OF_SCOPE`. Intent membantu model; gate runtime tetap otoritatif.

**B2 — Klarifikasi.** Jika permintaan data tidak menyebut indikator/topik yang dapat dicari, agent mengajukan tepat satu pertanyaan paling menentukan. Tidak boleh menanyakan periode sebelum kandidat `S#`/`T#` dipilih karena periode sah berasal dari kandidat.

**B3 — Tool loop.** Maksimum per giliran: 6 model request, 10 tool execution, 2 canonical call identik, deadline 120 detik. Attempt yang melampaui batas ditolak sebelum request/eksekusi. Tool error selalu berupa object berkode dan tidak dilempar ke model sebagai exception mentah.

**B4 — Frame.** Kandidat hanya sah bila berasal dari hasil tool pada pencarian aktif. Pilihan dapat berupa kode eksplisit atau judul normalisasi exact-unique; tafsir model hanya proposal yang harus di-resolve runtime.

**B5 — Topik baru.** Bila intent baru jelas berbeda dari query aktif, agent meminta konfirmasi. `ya/ganti` membuang frame dan memulai pencarian baru; `tidak/batal` mempertahankan frame. Input ambigu meminta klarifikasi, tidak membuang frame.

### 5.C Penemuan Data Resmi

**C1 — Pencarian SIMDASI.** Satu aksi pencarian memanggil adapter SIMDASI dan mengembalikan maksimal tiga kandidat pada halaman aktif.

**C2 — Pencarian Tabel Dinamis.** Aksi yang sama memanggil adapter Tabel Dinamis dan mengembalikan maksimal tiga kandidat pada halaman aktif.

**C3 — Pencarian Publikasi.** Aksi yang sama memanggil adapter Publikasi dan mengembalikan maksimal tiga kandidat pada halaman aktif. Ketiga grup disajikan berurutan: SIMDASI, Tabel Dinamis, Publikasi. Kegagalan satu adapter tidak membatalkan dua lainnya. Jika semua gagal/no-match, agent tidak membuat kandidat.

**C4 — Kode.** Prefix tertutup: SIMDASI `S`, Tabel Dinamis `T`, Publikasi `P`. Penomoran dimulai 1 per pencarian dan stabil. Judul berasal dari metadata resmi setelah HTML/script dibersihkan; model tidak menulis ulang judul.

**C5 — Pagination.** Maksimum 3 kandidat per sumber per halaman dan maksimum 6 halaman per pencarian. Halaman kedua melanjutkan `4–6`; halaman keenam paling tinggi `16–18`. Deduplikasi per sumber memakai identifier resmi; kandidat dari halaman lama tetap dapat dipilih sampai frame ditutup. “Lihat hasil berikutnya” hanya muncul bila minimal satu sumber `has_more=true` dan halaman aktif < 6. Setelah halaman keenam, UI menyatakan batas Prototype 1 tercapai dan meminta query yang lebih spesifik.

**C6 — Gate.** Fetch berdasarkan kode yang belum ditawarkan, kode beda prefix, kode dari frame lama, atau judul ambigu menghasilkan `selection_required`/`candidate_not_found`. Kandidat tunggal tetap butuh pilihan.

### 5.D Pengambilan dan Penyajian

**D1 — Periode tersedia.** Memilih `S#` memakai periode di metadata SIMDASI. Memilih `T#` memanggil daftar periode Tabel Dinamis. Periode diurutkan terbaru ke lama tetapi tidak dipilih otomatis. Tool mengembalikan maksimum 20 periode per halaman, maksimum 10 halaman; kode periode yang tampil diakumulasi pada `offered_periods`. Aksi “Lihat periode berikutnya” meminta page berikutnya dan hanya muncul bila `has_more=true`.

**D2 — Gate periode.** Hanya nilai periode yang pernah ditawarkan untuk kandidat aktif sah. Tahun yang tidak tersedia menghasilkan `period_not_available` beserta daftar periode sah.

**D3 — Fetch.** Runtime menyuntikkan domain `1306`, kandidat terpilih, dan periode terpilih. Respons harus lulus: `answerable=true`, `metadata.complete=true`, `metadata.missing=[]`, identifier cocok kandidat, periode cocok, dan cakupan domain valid.

**D4 — Penyajian data.** Bubble data memuat tepat delapan unsur: nilai, satuan, periode, cakupan, indikator, judul sumber, jenis sumber, URL resmi. Multi-baris menampilkan maksimal 10 baris per bubble serta jumlah total dan status `truncated`. Angka disalin dalam format tampilan Indonesia; tidak dikonversi oleh model.

**D5 — Publikasi.** Pemilihan `P#` menampilkan judul, abstraksi, dan URL resmi. Abstraksi kosong ditulis “Abstraksi tidak tersedia pada metadata BPS.” Tidak ada periode/fetch angka.

### 5.E Pengetahuan Terverifikasi

**E1 — Glosarium.** Tool mencari konsep pada endpoint resmi model `glosarium` dan menormalisasi `konsep`, `definisi`, `judulIndikator`, `satuan`, `sumberKonten`, serta identifier. Maksimum 3 hasil relevan. Upstream 500/schema invalid menjadi `glossary_unavailable`; model tidak mengisi kekosongan.

**E2 — KB PST.** File sumber memiliki metadata tertutup: `source_key`, `title`, `source_url` nullable, `verified` boolean, `verified_by`, `verified_at`, dan isi per heading. Hanya `verified=true` yang dapat dicari. Identitas/jam/prosedur tidak boleh berasal dari config runtime.

**E3 — Atribusi.** Jawaban menyertakan label `Glosarium Web API BPS` atau judul dokumen KB, heading/konteks, dan URL resmi jika tersedia. Sumber KB tanpa URL memakai nama dokumen terverifikasi.

**E4 — Perbedaan.** Dua hasil relevan disajikan terpisah. Agent boleh menyebut kemiripan redaksi tetapi tidak menggabungkan atribusi. Pertentangan substantif disebut eksplisit lalu admin mock ditawarkan.

**E5 — No-match.** Glosarium dan KB kosong/gagal → “Saya belum menemukan sumber resmi yang cukup untuk menjawab itu.” lalu tawaran admin dan fallback Buku Tamu.

### 5.F Diskusi dan Analisis

**F1 — Follow-up.** Pertanyaan periode/dimensi lain memakai kandidat aktif. Bila sumber tidak menawarkan dimensi yang diminta, agent menampilkan dimensi resmi atau menyatakan tidak tersedia; tidak menebak label.

**F2 — Comparable.** Dua baris harus memiliki identifier indikator sama, satuan kanonik sama, cakupan kode sama, dan nilai numeric terverifikasi. Periode harus berbeda untuk perbandingan antarperiode. Gagal satu syarat → `rows_not_comparable` dengan alasan tertutup: `indicator`, `unit`, `coverage`, `period`, atau `unverified`.

**F3 — Selisih.** `difference = ending_value - starting_value` menggunakan `Decimal` dari nilai kanonik, bukan string tampilan.

**F4 — Perubahan persen.** `percent_change = difference / starting_value × 100`; nilai awal nol menghasilkan `zero_baseline`. Tampilan dibulatkan dua angka desimal dengan `ROUND_HALF_UP`; nilai internal tidak dibulatkan sebelum operasi selesai.

**F5 — Arah.** Selisih positif=`naik`, negatif=`turun`, nol=`tetap`. Jawaban memuat dua nilai, cakupan, periode, satuan, rumus, hasil, arah, judul, dan URL sumber.

### 5.G Guardrail

**G1.** Field `domain` dari user/model ditolak `scope_domain_not_allowed`; runtime memakai literal `1306`.

**G2.** Token angka dibagi menjadi `verified`, `derived`, `sourced_knowledge`, `quoted_user`, dan `structural`. Hanya `verified`/`derived` boleh menjadi observasi data statistik. `sourced_knowledge` hanya boleh muncul dalam definisi/prosedur yang merupakan kutipan atau ringkasan setia Glosarium/KB terverifikasi dan wajib beratribusi; tipe ini tidak boleh dipakai untuk menjawab nilai indikator. `quoted_user` harus berfrasa “menurut informasi Kakak”.

**G3.** Candidate Publication tidak pernah masuk frame data aktif atau whitelist angka.

**G4.** Nilai ditahan bila salah satu dari nilai, satuan, periode, cakupan, indikator, judul/jenis sumber, atau URL resmi tidak valid.

**G5.** Prompt override, identity override, disclosure, tool abuse, instruksi dari tool/KB, script/HTML aktif, URL di luar allowlist, malformed JSON, timeout, 401, 429, 5xx, dan loop berulang tidak boleh menghasilkan fakta baru. Rahasia tidak dicatat atau dikirim ke browser/model.

### 5.H Handover Mock

**H1.** User yang meminta admin atau kebutuhan yang tidak tuntas menerima pilihan “Hubungi admin” dan “Isi Buku Tamu”. Tidak ada side effect manusia nyata.

**H2.** Memilih admin menghasilkan status mock eksplisit: “Prototype ini belum tersambung ke petugas. Simulasikan petugas tidak tersedia?” Memilih simulasi menghasilkan `admin_unavailable`.

**H3.** `admin_unavailable`, pengguna tidak mau menunggu, atau kegagalan sumber berakhir pada URL exact `https://s.bps.go.id/tamu1306`. URL berasal dari identity config tervalidasi, tidak diubah, dan tidak di-resolve/fetch oleh backend.

## 6. Alur utama

### 6.1 Permintaan data

```text
Rina → "data jumlah penduduk Padang Pariaman"
Marawa → search ketiga katalog → tampilkan S#/T#/P#
Rina → "S1"
Marawa → tampilkan periode resmi
Rina → "2024"
Marawa → fetch gated domain 1306 → tampilkan delapan unsur provenance
```

### 6.2 Analisis

```text
Rina → "bandingkan dengan 2023"
Marawa → fetch periode 2023 pada kandidat aktif
runtime → validasi comparable → Decimal difference + percent
Marawa → dua nilai + rumus + 4.514 jiwa + 1,05% + naik + sumber
```

### 6.3 Definisi dan fallback

```text
Rina → "apa arti indikator X?"
Marawa → Glosarium → KB
hasil kosong/error → jujur belum punya sumber
→ tawarkan admin mock → jika tak tersedia/tidak mau → Buku Tamu
```

## 7. Kebutuhan non-fungsional

- Browser target: Chrome/Edge/Firefox dua versi mayor terbaru; viewport minimum 360×640.
- Server Prototype 1 hanya bind ke `127.0.0.1`; akses jaringan/non-loopback berada di luar scope.
- Touch target minimum 44×44 CSS px; tinggi app memakai `100dvh`.
- Respons endpoint sesi p95 < 300 ms lokal; turn tanpa tool p95 < 3 detik; turn dengan sumber live p95 < 15 detik; hard deadline 120 detik.
- Maksimum input 8.000 karakter; maksimum output 12.000 karakter per turn; transcript browser 100 bubble; state server 40 pesan; sesi idle 2 jam.
- Maksimum 20 turn per sesi per jam; maksimum 10 sesi aktif dari satu IP lokal; respons `429` tidak menghapus state.
- API key hanya server-side; `.env`, prompt, argumen raw tool, dan exception trace tidak pernah masuk response.
- Request mutating hanya menerima origin loopback exact; cross-site request ditolak. Static response memakai CSP self-only, frame denial, dan menonaktifkan camera/microphone/geolocation.
- Source URL output wajib HTTPS dan host allowlist: `bps.go.id` serta subdomainnya, ditambah `s.bps.go.id`.
- Log prototype hanya event teknis tersanitasi tanpa isi percakapan; hilang saat restart.

## 8. Di luar cakupan Prototype 1

- WhatsApp/Evolution API, dashboard, admin nyata, takeover/relay, timeout, petugas/superadmin.
- Database, migrasi, durable inbox/outbox, multi-process/multi-replica, deployment production.
- Voice, gambar, file, OCR, ekstraksi isi PDF publikasi.
- Angka wilayah selain domain `1306` dan turunannya.
- SIRuSa sampai API resmi terverifikasi; scraper SIRuSa dilarang.
- Jawaban fakta dari ingatan model, web search bebas, atau publikasi sebagai sumber angka.
- Analisis selain selisih, perubahan persen, dan arah; rasio antardua indikator ditunda karena aturan comparable saat ini mewajibkan indikator sama.
- Guardrail keamanan production penuh, penyimpanan audit, dan moderation dashboard.

## 9. Definition of Done

| Modul | Bukti selesai |
|---|---|
| A | Refresh mempertahankan transcript; restart menghasilkan sesi kedaluwarsa; reset bersih; desktop dan 360 px lolos inspeksi. |
| B | Intent/loop/frame/ganti topik lulus skenario A dan B di TEST-SCENARIOS; loop berhenti pada budget. |
| C | Tiga katalog tampil berkelompok, 3/sumber, kode stabil lintas halaman, no auto-select. |
| D | Fetch sebelum kandidat/periode ditolak; jawaban S/T memuat delapan unsur; P hanya metadata. |
| E | Glosarium fixture + KB verified lulus; no-match tidak menghasilkan definisi model; smoke live Glosarium minimal satu kali hijau sebelum rekomendasi fase 2. |
| F | Semua operasi menggunakan `Decimal`; fixture 430.000→434.514 menghasilkan 4.514 dan 1,05%; seluruh penolakan comparable lulus. |
| G | Scope/provenance/malformed API/prompt injection/secret leakage lulus skenario G. |
| H | Admin jelas mock dan semua jalur gagal menawarkan URL Buku Tamu resmi. |
| Prototype | Seluruh 80 skenario TEST-SCENARIOS lulus, unit/contract test hijau, dan smoke Web API BPS terdokumentasi. |

## 10. Dokumen terkait

- FEATURES.md — peta scope dan ID stabil.
- ARCHITECTURE.md — stack, komponen, state, failure strategy.
- DATABASE.md — kontrak state in-memory dan browser; keputusan tanpa database.
- API-SPEC.md — REST serta kontrak tool internal.
- AGENT.md — persona, prompt, tool, state, guardrail.
- TEST-SCENARIOS.md — 80 acceptance scenario normatif.
- TASKS.md — urutan implementasi.
- DECISIONS.md — keputusan mengikat.
- AGENTS.md — aturan developer/coding agent.
