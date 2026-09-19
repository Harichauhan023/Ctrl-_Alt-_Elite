# 🚀 GeoReady-AI — Step-by-Step Run Guide

## Keys required: **ZERO**

| Service | Key? | Notes |
|---|---|---|
| Map tiles (OpenFreeMap) | ❌ keyless | Auto offline-safe fallback if Wi-Fi dies |
| Gemini AI | ⚠️ optional | App works 100% without it (deterministic explainer) |
| HuggingFace MiniLM | ❌ | One-time ~35 MB download on first backend start |

## Order of operations

```text
1 ─ python venv + pip install -r backend/requirements.txt
2 ─ cd frontend && npm install && cd ..
3 ─ DATA: already in data/ if you copied the full folder ✅
      otherwise → python scripts/generate_data.py
      rate-limited? → wait 60s → python scripts/fetch_osm.py
4 ─ PROD DEMO: cd frontend && npm run build && cd ..
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
     → http://localhost:8000        (docs at /docs)

   DEV MODE: terminal 1 → uvicorn …:8000   |   terminal 2 → npm run dev
     → http://localhost:5173
5 ─ optional: copy .env.example → .env, add 1–4 Gemini keys, restart backend
6 ─ verify: python -m pytest tests/ -q   → 12 passed
```

## First startup takes 20–60s
loads 8 layers → builds 649 H3 zones → downloads MiniLM once.
Wait for `✔ RAG ready` + `Uvicorn running`.

## First demo clicks
Dashboard → Map → toggle 5 layers → 🔥 heatmap → click **Old City Core** →
drag weight sliders (score + heatmap morph live) → click **river pocket** (⛔ NOT SUITABLE)
→ Catchment → ✨ Explain → Compare 2–3 sites → PDF report.

Full judge walkthrough: `docs/DEMO_SCRIPT.md`
