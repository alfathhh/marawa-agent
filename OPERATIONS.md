# Operasional Marawa Fase 2

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
POST https://<origin>/hooks/webhook
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