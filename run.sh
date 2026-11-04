#!/bin/bash
# Starts the API on http://localhost:8000 (docs at /docs) using the local SQLite db.
set -e
cd "$(dirname "$0")"
export DATABASE_URL="sqlite:///./femalogy-dev.db"
.venv/bin/alembic upgrade head
exec .venv/bin/uvicorn app.main:app --reload
