#!/bin/sh
set -eu
# Fails early on unsafe production configuration.
PYTHONPATH=backend python -c 'from app.config import settings; settings.validate()'
# Render runs migrations in its pre-deploy step. Standalone Docker runs them here.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  python -m alembic -c backend/alembic.ini upgrade head
fi
exec python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-10000}" --workers 1 --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
