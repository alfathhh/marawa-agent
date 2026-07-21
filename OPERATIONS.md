# Operasional Marawa Fase 2

## Full Docker stack

```bash
cp .env.example .env
chmod 600 .env
# Isi semua secret kosong, lalu:
docker compose pull
docker compose build
docker compose up -d
```

Stack tunggal menyediakan app/dashboard `127.0.0.1:8020`, Evolution `127.0.0.1:8082`, satu worker, PostgreSQL 17, PostgreSQL Evolution 15, dan Redis 7. Migration hingga `head` serta bootstrap superadmin pertama berjalan sebelum app/worker. Evolution dipin ke `v2.3.7`, bukan `latest`.

Akun bootstrap wajib mengganti password sementara. KB awal berstatus **DUMMY / BELUM DIVERIFIKASI** dan hanya dapat diedit superadmin. Webhook internal adalah `http://app:8080/webhooks/evolution` dengan `X-Webhook-Secret`. `https://s.bps.go.id/...` adalah shortlink resmi BPS.

Rollback dump rebuild 21 Juli 2026 berada di `~/backups/marawa-rebuild-20260721T152356Z/`.

## Prasyarat

- PostgreSQL 17
- Evolution API v2 instance
- Python virtualenv dari requirements prototype + `requirements-operational.txt`

## Konfigurasi wajib

```text
DATABASE_URL
EVOLUTION_API_URL
EVOLUTION_API_KEY
EVOLUTION_INSTANCE
WEBHOOK_SECRET              # minimal 32 karakter
DASHBOARD_SESSION_SECRET    # minimal 32 karakter acak
DASHBOARD_ORIGIN            # exact HTTPS origin production
APP_ENV=production
```

Tidak ada password atau secret default di repository.

## Migration

```bash
.venv/bin/alembic -c alembic.ini upgrade head
```

`sqlalchemy.url` wajib diinjeksi oleh environment/deployment wrapper; jangan commit credential ke `alembic.ini`.

## Bootstrap superadmin

Generate hash lokal lalu insert melalui transaction terkontrol. Gunakan `operational.dashboard_security.hash_password()`; jangan menaruh password plaintext di shell history atau migration.

## Run

```bash
.venv/bin/uvicorn operational.main:app --host 127.0.0.1 --port 8080 --workers 1
```

Ceiling MVP: satu process/worker. Upgrade ke connection-per-request sebelum multi-worker/multi-replica.

Webhook Evolution diarahkan ke:

```text
POST https://<origin>/webhooks/evolution
X-Webhook-Secret: <WEBHOOK_SECRET>
```

Dashboard:

```text
https://<origin>/dashboard
```

## Production gate yang belum selesai

- inject runtime Gemini + Web API BPS ke inbound worker;
- Evolution live upsert/send/update;
- signoff KB dan registry wilayah oleh PIC;
- backup, monitoring, HTTPS/reverse proxy, dan UAT mobile nyata;
- deploy production memerlukan keputusan terpisah.