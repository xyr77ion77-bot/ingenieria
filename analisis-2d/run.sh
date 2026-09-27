#!/usr/bin/env bash
# Lanza el servidor de Análisis Estructural 2D (backend + frontend)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creando entorno virtual..."
  python3 -m venv .venv
  .venv/bin/pip install --quiet -r backend/requirements.txt
fi
exec .venv/bin/uvicorn backend.api:app --host 0.0.0.0 --port 8000
