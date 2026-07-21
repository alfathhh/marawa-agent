# FEATURES.md — Peta Fitur Marawa Prototype 1

> Versi 1.0 · 21 Juli 2026
> Hierarki fitur → sub-fitur Prototype 1. ID di sini dirujuk oleh PRD §5, API-SPEC, AGENT, dan TASKS.
> Status: `Direncanakan` → `Dikerjakan` → `Selesai`.

## 1. Outcome dan batas

**Outcome:** membuktikan lewat web chat lokal bahwa Marawa dapat mencari, menjelaskan, dan membandingkan data resmi BPS Kabupaten Padang Pariaman tanpa mengarang angka atau fakta.

Prototype 1 bukan kanal pelayanan operasional. WhatsApp, Evolution API, dashboard petugas, relay manusia, autentikasi, dan deployment production berada setelah gate 80 skenario lulus.

## 2. Peta ringkas

```text
Marawa Prototype 1
├── A. Web Chat Lokal              (A1 chat · A2 tahan refresh · A3 reset · A4 sesi kedaluwarsa)
├── B. Orkestrasi Percakapan       (B1 intent · B2 klarifikasi · B3 tool loop · B4 frame · B5 ganti topik)
├── C. Penemuan Data Resmi         (C1 SIMDASI · C2 Tabel Dinamis · C3 Publikasi · C4 kode · C5 paging · C6 gate)
├── D. Pengambilan & Penyajian     (D1 periode · D2 gate periode · D3 fetch · D4 provenance · D5 publikasi)
├── E. Pengetahuan Terverifikasi   (E1 Glosarium · E2 KB · E3 atribusi · E4 konflik · E5 no-match)
├── F. Diskusi & Analisis          (F1 follow-up · F2 comparable · F3 selisih · F4 persen · F5 arah)
├── G. Guardrail                   (G1 domain · G2 provenance · G3 publikasi · G4 metadata · G5 fallback)
└── H. Handover Mock               (H1 admin · H2 status mock · H3 Buku Tamu)
```

## 3. Detail modul

### A. Web Chat Lokal

Nilai: pengguna dapat menguji percakapan Marawa tanpa WhatsApp. Dependensi: tidak ada.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| A1 | Percakapan dua arah | Pengguna mengirim teks dan menerima bubble jawaban atau pilihan terstruktur. | Direncanakan |
| A2 | Transcript tahan refresh | Browser menyimpan transcript, `session_id`, dan generasi server; refresh tidak menghapus tampilan. | Direncanakan |
| A3 | Percakapan baru | Tombol reset menghapus transcript browser dan frame server yang masih hidup. | Direncanakan |
| A4 | Sesi kedaluwarsa | Restart server atau idle 2 jam menghasilkan `session_expired`; UI tidak merekonstruksi state dari transcript. | Direncanakan |

Detail: PRD §5.A · API-SPEC §1–§2 · TASKS M1.

### B. Orkestrasi Percakapan

Nilai: percakapan natural tetap tunduk pada state dan gate deterministik. Dependensi: A.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| B1 | Klasifikasi kebutuhan | Agent membedakan data, definisi, layanan PST, analisis, dan permintaan admin. | Direncanakan |
| B2 | Klarifikasi | Kebutuhan yang belum cukup dijawab dengan satu pertanyaan klarifikasi paling menentukan. | Direncanakan |
| B3 | Tool-calling multi-langkah | Model dapat mencari, membaca hasil tool, meminta pilihan, dan melanjutkan sampai jawaban final. | Direncanakan |
| B4 | Frame aktif | Satu sesi menyimpan tepat satu pencarian aktif: query, kandidat, pilihan, periode, dan baris terverifikasi. | Direncanakan |
| B5 | Pergantian topik | Topik baru menutup frame lama hanya setelah konfirmasi pengguna. | Direncanakan |

Detail: PRD §5.B · AGENT §3–§6 · TASKS M2.

### C. Penemuan Data Resmi

Nilai: pengguna melihat alternatif resmi dan memilih sendiri. Dependensi: B, G.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| C1 | Cari SIMDASI | Pencarian mengembalikan maksimal 3 kandidat SIMDASI per halaman. | Direncanakan |
| C2 | Cari Tabel Dinamis | Pencarian mengembalikan maksimal 3 kandidat Tabel Dinamis per halaman. | Direncanakan |
| C3 | Cari Publikasi | Pencarian mengembalikan maksimal 3 kandidat Publikasi per halaman. | Direncanakan |
| C4 | Kode kandidat | Kandidat memakai `S#`, `T#`, `P#`; kode unik dan stabil selama pencarian aktif. | Direncanakan |
| C5 | Halaman berikutnya | Halaman kedua melanjutkan nomor 4–6 tanpa mengubah kode halaman pertama. | Direncanakan |
| C6 | Pilihan eksplisit | Kandidat tunggal pun tidak boleh dipilih otomatis; kode yang tidak pernah ditawarkan ditolak. | Direncanakan |

Detail: PRD §5.C · AGENT §4 · TASKS M3.

### D. Pengambilan dan Penyajian

Nilai: angka hanya keluar setelah sumber dan periode dipilih. Dependensi: C, G.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| D1 | Daftar periode | Setelah `S#`/`T#` dipilih, sistem menampilkan periode resmi tersedia. | Direncanakan |
| D2 | Pilihan periode | Fetch ditolak sampai pengguna memilih periode yang pernah ditawarkan. | Direncanakan |
| D3 | Fetch data | Sistem mengambil baris SIMDASI/Tabel Dinamis untuk kandidat dan periode terpilih pada domain runtime `1306`. | Direncanakan |
| D4 | Provenance lengkap | Jawaban angka memuat nilai, satuan, periode, cakupan, indikator, judul, jenis sumber, dan URL resmi. | Direncanakan |
| D5 | Metadata publikasi | `P#` hanya menghasilkan judul, abstraksi atau status abstraksi kosong, dan URL resmi. | Direncanakan |

Detail: PRD §5.D · API-SPEC §4 · TASKS M3.

### E. Pengetahuan Terverifikasi

Nilai: definisi dan layanan tidak berasal dari ingatan model. Dependensi: B, G.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| E1 | Glosarium Web API BPS | Konsep dicari lewat model resmi `glosarium`; error upstream menjadi `glossary_unavailable`. | Direncanakan |
| E2 | Knowledge base PST | Fakta lokal hanya diambil dari dokumen berstatus `verified=true`. | Direncanakan |
| E3 | Atribusi | Jawaban pengetahuan memuat judul/heading, jenis sumber, dan URL atau nama dokumen terverifikasi. | Direncanakan |
| E4 | Perbedaan sumber | Definisi berbeda ditampilkan terpisah; pertentangan tidak diputus model. | Direncanakan |
| E5 | No-match | Tidak ada sumber → jujur belum punya catatan → tawaran admin → Buku Tamu. | Direncanakan |

Detail: PRD §5.E · AGENT §5 · TASKS M4.

### F. Diskusi dan Analisis

Nilai: pengguna dapat memahami dan membandingkan baris resmi tanpa hitungan LLM. Dependensi: D, E.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| F1 | Follow-up data aktif | Periode/dimensi lain diambil dari kandidat aktif tanpa pencarian katalog ulang. | Direncanakan |
| F2 | Validasi comparable | Dua baris harus sama indikator, satuan, dan cakupan sebelum dihitung. | Direncanakan |
| F3 | Selisih absolut | Runtime `Decimal` menghitung nilai akhir − nilai awal. | Direncanakan |
| F4 | Perubahan persen | Runtime menghitung `(akhir-awal)/awal×100`, dibulatkan 2 desimal `ROUND_HALF_UP`; nilai awal nol ditolak. | Direncanakan |
| F5 | Arah perubahan | `naik`, `turun`, atau `tetap` diturunkan dari tanda selisih runtime. | Direncanakan |

Detail: PRD §5.F · AGENT §4–§5 · TASKS M4.

### G. Guardrail

Nilai: kegagalan model atau sumber tidak berubah menjadi fakta palsu. Dependensi: tidak ada.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| G1 | Kunci domain | Domain tidak ada di schema model; runtime selalu menyuntikkan literal string `1306`. | Direncanakan |
| G2 | Provenance bertipe | Observasi data harus berasal dari baris terverifikasi/hasil `Decimal`; angka definisi/layanan hanya boleh dari Glosarium/KB terverifikasi dan tetap beratribusi. | Direncanakan |
| G3 | Batas Publikasi | Metadata publikasi tidak pernah mengotorisasi klaim angka. | Direncanakan |
| G4 | Metadata wajib | Nilai ditahan bila nilai, satuan, periode, cakupan, indikator, atau sumber tidak lengkap. | Direncanakan |
| G5 | Fallback jujur | Tool/LLM gagal → tidak ada fakta baru; tampilkan status sumber dan jalur eskalasi. | Direncanakan |

Detail: PRD §5.G · ARCHITECTURE §5 · TASKS M2–M5.

### H. Handover Mock

Nilai: alur eskalasi dapat diuji tanpa membangun dashboard palsu. Dependensi: A, B.

| ID | Sub-fitur | Perilaku teruji | Status |
|---|---|---|---|
| H1 | Tawaran admin | Permintaan manusia atau kebutuhan tak tuntas menghasilkan tawaran menghubungi admin. | Direncanakan |
| H2 | Status simulasi | Prototype menyatakan admin belum benar-benar terhubung dan dapat mensimulasikan `tidak tersedia`. | Direncanakan |
| H3 | Buku Tamu | Tidak dijawab/tidak tersedia/tidak mau menunggu → link `https://s.bps.go.id/tamu1306`. | Direncanakan |

Detail: PRD §5.H · AGENT §6–§7 · TASKS M5.

## 4. Roadmap setelah Prototype 1 — bukan scope implementasi paket ini

```text
FASE 2 — Kanal operasional
├── Evolution API + WhatsApp
├── inbox/outbox tahan restart
├── dashboard petugas
├── takeover/relay melalui nomor bot
└── timeout admin + fallback Buku Tamu nyata

FASE 3 — Operasi lengkap
├── auth petugas/superadmin
├── kelola pengguna
├── pengaturan webhook, Evolution, jam, dan timeout
├── kelola knowledge base
└── audit, statistik, dan observabilitas
```

Roadmap tidak memiliki ID sub-fitur di paket ini; implementasinya memerlukan gerbang keputusan dan paket spesifikasi baru setelah 80 skenario Prototype 1 lulus.

## 5. Ringkasan beban

| Scope | Modul | Sub-fitur aktif |
|---|---:|---:|
| Prototype 1 | A–H | 38 |
| Roadmap | Belum menjadi kontrak implementasi | 0 |
