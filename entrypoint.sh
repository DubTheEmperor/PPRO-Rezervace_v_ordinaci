#!/bin/sh
set -e

echo "=== Čekání na připravenost PostgreSQL databáze ==="
# Spuštění migrací Alembic
echo "=== Provádění databázových migrací (Alembic) ==="
# Při selhání migrace kontejner skončí s chybou (set -e) – aplikace nesmí běžet nad nekonzistentním schématem
alembic upgrade head

echo "=== Spouštění FastAPI aplikace přes Uvicorn ==="
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
