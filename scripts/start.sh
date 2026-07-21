#!/bin/sh
set -eu

case "${1:-app}" in
  migrate) alembic upgrade head && exec python3 -m operational.bootstrap ;;
  app) exec uvicorn operational.main:app --host 0.0.0.0 --port 8080 --workers 1 ;;
  worker) exec python3 -m operational.worker ;;
  *) echo "usage: $0 {migrate|app|worker}" >&2; exit 2 ;;
esac
