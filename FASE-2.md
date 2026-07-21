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

- Schema PostgreSQL: users, settings, contacts, conversations, inbound events, messages, outbound messages, handover sessions, audit log.
- Unique idempotency key untuk inbound Evolution dan outbox dedupe.
- Migration awal dan repository tests.

### P1 — Evolution boundary

- Parser `messages.upsert`, abaikan grup/fromMe/media unsupported.
- Parser `messages.update` dan status monotonic.
- Connection status/QR/logout.
- Outbox worker; `sendText` hanya menghasilkan `ACCEPTED`.

### P2 — Agent bridge

- Pesan inbound masuk agent runtime Marawa.
- Jawaban/provenance dirender WhatsApp-safe.
- Provider/BPS failure menghasilkan fallback aman dan tidak kehilangan inbound.

### P3 — Handover

- Tawaran, start, claim atomik first-wins, relay, resolve/cancel.
- Timeout klaim, first reply, admin idle, user idle.
- Semua terminal path mengembalikan state bot secara konsisten.

### P4 — Dashboard

- Auth/role/CSRF/session invalidation.
- Inbox real-time, claim/reply/resolve.
- Superadmin users/settings/Evolution/KB.
- Audit dan masking data.

### P5 — Acceptance

- Unit/contract/integration test semua state.
- Restart recovery inbox/outbox.
- Evolution live: upsert masuk, send accepted, `messages.update` delivery atau error terbukti.
- Browser desktop/mobile dan security review.

## Gate implementasi

- Package fase 2 berada di `operational/`; `prototype_v1/` tetap regression oracle.
- Semua perubahan non-trivial TDD.
- Tidak ada deploy atau perubahan VPS/service sebelum izin eksekusi terpisah.
- Secret hanya environment/server-side; tidak masuk Git, browser, log, atau audit detail.