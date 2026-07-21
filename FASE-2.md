# FASE-2.md — Kanal Operasional WhatsApp dan Dashboard

> Keputusan PO · 21 Juli 2026

## Outcome

Menghubungkan kemampuan Marawa Prototype 1 ke WhatsApp melalui Evolution API dan menyediakan dashboard petugas untuk handover, konfigurasi, pengguna, serta status operasional. Fase ini tidak mengubah aturan sumber fakta Prototype 1.

## Scope MVP

1. Webhook Evolution menerima `messages.upsert` dan `messages.update` secara idempoten.
2. Durable inbox/outbox tahan restart dengan PostgreSQL.
3. Pengiriman `sendText` memiliki dua tahap: `ACCEPTED` saat Evolution menerima request dan status delivery dari `messages.update` (`ERROR`, `SERVER_ACK`, `DELIVERY_ACK`, `READ`, `PLAYED`).
4. Dashboard login untuk `superadmin` dan `petugas`, dengan CSRF, session expiry, role check server-side, audit, serta masking nomor untuk petugas.
5. Dashboard menampilkan inbox percakapan, claim/takeover, reply melalui nomor bot, resolve, timeout, dan fallback Buku Tamu.
6. Superadmin dapat mengelola pengguna, konfigurasi Evolution/webhook, jam layanan, timeout, status bot, dan knowledge seed.
7. Connection status, pairing QR, dan logout instance Evolution tersedia tanpa mengekspos API key atau payload provider mentah.

## Non-goal MVP

- Multi-tenant/multi-instance Evolution.
- Multi-replica sebelum locking/outbox diuji pada PostgreSQL.
- Voice/OCR/file ingestion.
- Auto-retry pesan berstatus `ERROR` tanpa kebijakan dedupe eksplisit.
- Klaim production-ready selama secret, backup, monitoring, dan UAT deployment belum selesai.

## State utama

```text
Conversation: BOT_ACTIVE → HANDOVER_PENDING → HUMAN_ACTIVE → BOT_ACTIVE
Handover: PENDING → ACTIVE → RESOLVED | FAILED | EXPIRED
Outbound: QUEUED → SENDING → ACCEPTED → SERVER_ACK → DELIVERY_ACK → READ | PLAYED
                                      └→ ERROR
```

`ACCEPTED` bukan bukti delivery. Webhook status boleh datang terlambat, berulang, atau tidak berurutan; update wajib idempoten dan tidak boleh menurunkan status terminal/progress yang lebih tinggi, kecuali `ERROR` memiliki evidence provider yang lebih baru.

## Milestone

### P0 — Kontrak dan persistence

- [x] Migration PostgreSQL awal untuk durable inbound, outbound, dan early receipt.
- [x] Unique idempotency key inbound dan nullable unique outbox dedupe.
- [x] Migration upgrade/downgrade, duplicate admission, receipt reconciliation, dan monotonic delivery diuji pada PostgreSQL 17 disposable.
- [x] Users, settings, handover, dan audit ditambahkan surgical pada milestone yang pertama memakainya; contacts/conversations tidak dibuat karena queue + handover sudah memenuhi MVP.

### P1 — Evolution boundary

- [x] Parser `messages.upsert`, abaikan grup/fromMe/media unsupported.
- [x] Parser `messages.update` dan status monotonic.
- [x] Authenticated webhook dengan body limit dan exact production instance.
- [x] Connection status, QR PNG tervalidasi, dan logout.
- [x] Outbox worker dengan `SKIP LOCKED`, ordering per nomor, lease recovery 90 detik, bounded retry/dead-letter; `sendText` hanya menghasilkan `ACCEPTED`.

### P2 — Agent bridge

- [x] Durable inbound worker memasukkan pesan ke runtime contract Marawa.
- [x] Jawaban/provenance official BPS dirender WhatsApp-safe dan dideduplikasi ke outbox.
- [x] Provider/BPS failure menghasilkan bounded retry/dead-letter tanpa jawaban palsu.
- [ ] Production composition wajib menginjeksi runtime Gemini+BPS; `ProviderMock` prototype tidak pernah dipakai untuk WhatsApp.

### P3 — Handover

- [x] Request, claim atomik first-wins, fenced relay, release, resolve/cancel.
- [x] Claim deadline, first reply, admin idle, user idle, dan restart recovery.
- [x] Semua terminal path mengembalikan state bot secara konsisten.

### P4 — Dashboard

- [x] Signed HttpOnly session, role, CSRF, exact Origin, dan immediate session invalidation.
- [x] Inbox queue, claim/reply/release/resolve melalui PostgreSQL backend.
- [x] Superadmin users/settings dan Evolution status/QR/logout contract.
- [x] Audit mutation, masking nomor, responsive static dashboard tanpa build step.
- [ ] Knowledge seed management ditunda: seed prototype file-based dan belum punya signoff PIC.

### P5 — Acceptance

- [x] Unit/contract/integration PostgreSQL semua state: 317 passed pada 21 Juli 2026.
- [x] Lease-based restart recovery inbox/outbox.
- [ ] Evolution live: butuh URL/API key/instance dan nomor WhatsApp UAT nyata.
- [x] Browser desktop login/navigation/degraded Evolution dan security headers diuji nyata; responsive 360px dijaga contract CSS, mobile screenshot belum diambil karena browser resize runner tidak tersedia.

## Gate implementasi

- Package fase 2 berada di `operational/`; `prototype_v1/` tetap regression oracle.
- Semua perubahan non-trivial TDD.
- Tidak ada deploy atau perubahan VPS/service sebelum izin eksekusi terpisah.
- Secret hanya environment/server-side; tidak masuk Git, browser, log, atau audit detail.