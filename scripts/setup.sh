#!/usr/bin/env bash
# GeoReady-AI — one-command setup (deps + data). Then:
#   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PYTHON:-python3}
echo "▶ Python deps…"
$PY -m pip install --quiet -r backend/requirements.txt

echo "▶ Frontend deps…"
(cd frontend && npm install --no-audit --no-fund --silent)

if [ -f data/roads.geojson ] && [ -f data/population.geojson ]; then
  echo "▶ Geospatial data already present (shipped in repo) ✓"
else
  echo "▶ Generating geospatial data (Rajkot)…"
  $PY scripts/generate_data.py
fi

echo "▶ Frontend production build…"
(cd frontend && npm run build >/dev/null)

echo ""
echo "✅ Setup complete. Start the app:"
echo "   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "   → open http://localhost:8000  (API docs at /docs)"
echo ""
echo "Optional AI mode: cp .env.example .env  → add 1-4 Gemini keys."
