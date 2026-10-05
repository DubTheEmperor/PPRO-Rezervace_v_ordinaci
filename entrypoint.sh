#!/bin/sh
set -e

echo "=== Čekání na připravenost PostgreSQL databáze ==="
# Spuštění migrací Alembic
echo "=== Provádění databázových migrací (Alembic) ==="
alembic upgrade head || echo "Upozornění: Migrace selhaly nebo tabulky již existují."

echo "=== Spouštění FastAPI aplikace přes Uvicorn ==="
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
