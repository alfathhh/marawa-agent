# Operational Phase Rules

Scope: `operational/` dan `tests/operational/`. `prototype_v1/` adalah regression oracle; jangan ubah kontrak faktanya untuk memudahkan fase ini.

## Outcome

Bangun satu kanal WhatsApp Evolution dan dashboard petugas/superadmin dengan durable inbox/outbox, delivery receipt, handover atomik, timeout, audit, dan konfigurasi operasional.

## Rules

1. TDD untuk setiap behavior non-trivial; full Prototype regression wajib tetap hijau.
2. Webhook wajib constant-time secret check, body limit, JSON object, exact instance production, dan idempotency sebelum acknowledgement sukses.
3. `sendText` 2xx berarti `ACCEPTED`, bukan delivered. Delivery berasal dari `messages.update`.
4. Inbox/outbox/handover/deadline harus durable dan recovery-tested; satu worker/replica sampai locking multi-replica terbukti.
5. Claim first-wins dan semua aksi owner memakai generation fence.
6. Dashboard mutation wajib auth, CSRF, role, ownership, rate limit, dan audit server-side.
7. Secret/payload mentah/nomor penuh petugas tidak masuk browser atau log. Superadmin dapat melihat nomor penuh; petugas dimasking.
8. Provider utama Gemini; 9router failure tidak boleh menghasilkan fakta tanpa sumber. Glosarium failure wajib fallback KB/no-match.
9. Dependency fase 2 dideklarasikan terpisah. Jangan install, menjalankan DB/service, deploy, atau mengubah VPS tanpa izin eksplisit.
10. Minimum files; jangan tambah framework frontend, service layer generik, repository abstraction, atau multi-tenant sebelum kebutuhan nyata.

## Verification

```bash
.venv/bin/python -m pytest tests/prototype_v1 tests/operational -q
.venv/bin/ruff check prototype_v1 operational tests/prototype_v1 tests/operational
git diff --check
```