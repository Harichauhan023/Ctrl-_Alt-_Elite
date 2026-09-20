# 🗺️ GeoReady-AI

**AI-Powered GeoSpatial Site Readiness Analyzer** — Bit N Build '26 · PS-2

> *"Where should we place a new facility — and what geographic factors explain its readiness score?"*

GeoReady-AI is an interactive geospatial decision-support platform that scores, compares, visualizes and
explains candidate locations for new facilities (EV chargers, retail, warehouses, telecom towers,
service centers, renewable sites) across the **Rajkot metropolitan area**.

![status](https://img.shields.io/badge/status-hackathon%20v2-22c55e) ![backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20PostGIS%2FDuckDB-38bdf8) ![ml](https://img.shields.io/badge/ML-RandomForest%20R%C2%B2%200.96-a78bfa) ![rag](https://img.shields.io/badge/RAG-MiniLM%20vector%20search-f59e0b)

---

## ⚡ Quickstart (fresh clone → running in ~3 minutes)

```bash
# 1. deps + data
bash scripts/setup.sh

# 2. run (UI + API on http://localhost:8000)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**No API keys, no Docker required** — the first boot auto-creates the embedded DuckDB database
(spatial + vector), seeds it from the GeoJSON layers, auto-ingests the 63 RAG document chunks
(embedding via local MiniLM ONNX), builds the H3 hotspot grid and the road routing graph.

Optional upgrades (all auto-detected):

| Upgrade | How |
|---|---|
| Google Gemini AI answers | copy `.env.example` → `.env`, add 1–4 keys (4-provider failover) |
| PostgreSQL + PostGIS + pgvector | `docker compose up -d` then set `DATABASE_URL` in `.env` |

Dev mode (hot reload): `uvicorn …:8000` + `cd frontend && npm run dev` → http://localhost:5173.

---

## 🧭 The experience

| Page | What it is |
|---|---|
| **Chat** (landing) | Full decision assistant: RAG-grounded Q&A with **semantic top-k sources** (real `rag/documents/*.md` paths + cosine bars), engine actions (recommend / analyze / compare), jump-to-map buttons, typing animation |
| **Map** | Interactive Rajkot map · **basemap switcher (Satellite / Streets / Dark)** · click-to-analyze · H3 readiness heatmap · layer toggles + opacity · draw-an-area · catchment rings · ghost-rival what-ifs · **closable panels (X)** |
| Dashboard | City-level aggregate stats |
| Compare | 2–4 sites: factor table + **ML prediction row** + winner narrative |
| Analytics | Data-layer diagnostics |
| Knowledge | **RAG Explorer**: search the 63-chunk vector store, see mode (`pgvector` / `duckdb-vss` / `docs-memory`), scores and source-file chips |

## 🧠 Architecture

```
React/MapLibre ──/api──▶ FastAPI
                          ├─▶ Spatial DB  (PostgreSQL+PostGIS+pgvector ▸ embedded DuckDB fallback, SAME SQL)
                          │     └─ feature extraction: 10 radius/point-in-poly/nearest SQL queries per pin
                          ├─▶ Deterministic 5-factor scoring engine (0–100, Σ weights = 100)
                          ├─▶ ML: RandomForestRegressor (10,000 synthetic sites, 13 engineered features,
                          │       holdout MAE 1.85 · RMSE 2.33 · R² 0.959) — shown side-by-side with the
                          │       deterministic score; weight sliders never move the ML number
                          ├─▶ RAG: rag/documents/*.md → chunks → MiniLM(384-d) → vector table
                          │       (pgvector <+> / duckdb vss array_cosine_distance) → top-k + sources
                          ├─▶ Routing: OSM graph → networkx Dijkstra 10/20/30-min travel-sheds
                          └─▶ Gemini 4-provider failover → deterministic fallback (analysis never breaks)
```

**The geospatial engine computes facts and scores — the LLM only explains them.**
Same input + same weights ⇒ same score. AI failure can never break the analysis.

Deep dive: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 📂 Repository

```
├── backend/app/          # FastAPI: api/ geospatial/ scoring/ db/ rag/ ai/ services/
├── ml/                   # feature_schema + training_data.csv (10k) + models/ + training_report.json
├── rag/                  # documents/ (33 markdown docs → 63 chunks) · embeddings · ingest · retriever · test_retrieval
├── scripts/              # seed_database · generate_training_data · generate_data · fetch_osm · setup
├── data/                 # GeoJSON layers (Rajkot) + geoready.duckdb (auto-created)
├── docker-compose.yml    # PostgreSQL 16 + PostGIS + pgvector (hero DB mode)
├── docs/                 # ARCHITECTURE · DEMO_SCRIPT · PITCH · original PS docs
└── tests/                # 31 tests: scoring · geospatial/SQL parity · ML · RAG · AI
```

## 🛰️ Data strategy (honest & replaceable)

- **Real**: road network (1,538 ways), 176 hospitals/clinics, 12 schools, 8 fuel stations — OpenStreetMap (Overpass), plus the shop/POI census.
- **Synthetic, seeded from real geography**: H3 population model (~9 lakh people), land-use zones
  (Kalawad Rd strip, Aji industrial estate…), Aji-river flood-risk bands and EV-competitor top-up.
  Every synthetic feature is labelled in `rag/documents/datasets/*`; replacing with municipal/census
  GeoJSON needs **zero code changes**.

Full provenance: `rag/documents/datasets/`.

## 🧮 Scoring methodology (short)

Five factors, each 0–100, final = Σ factor × weight (Σ = 100 %):

| Factor | Method |
|---|---|
| Population | effective population ≤1.2 km, decay 0.6 km, normalized to city p95 demand |
| Accessibility | 60 % proximity to major roads (decay 1.2 km) + 40 % road density ≤600 m |
| Competition | counts ≤1/3 km, nearest distance; *avoid* or *attract* polarity per business |
| Land use | per-business category suitability matrix |
| Environment | worst intersecting risk polygon (low 100 → critical 0) |

**Hard constraints** — protected land or critical-risk pockets → `NOT_SUITABLE` regardless of score.
Every feature used by the rules engine is ALSO a RandomForest input, so the ML row in the UI is an
independent cross-check of the same reality.

Full methodology: `rag/documents/methodology/`.

## 🔌 API

`GET /api/health` · `GET /api/layers{,/{name}/data}` · `POST /api/analyze{,_all}` ·
`POST /api/compare` · `GET /api/hotspots` · `POST /api/catchment` · `POST /api/recommend` ·
`POST /api/polygon` · `POST /api/explain` · `POST /api/report` · `POST /api/chat` ·
`GET /api/rag/search` · `GET /api/ml/insights` · `GET/POST /api/sites` · docs at `/docs`.

## ✅ Testing

```bash
python3 -m pytest tests/ -q            # 31 tests
python3 rag/test_retrieval.py          # 10-query retrieval probe (needs the server OR free DB lock)
```

Covers: weight validation, determinism, bounds, hard constraints, polarity,
**dual-database feature parity (SQL vs memory)**, point-in-polygon / distances / radii,
ML artifact + schema + metric sanity, RAG chunk contract + semantic retrieval + source metadata,
AI fallback chain.


## 👥 Team & stack

React 18 · TypeScript · Tailwind · MapLibre GL · Recharts · Zustand ｜
FastAPI · GeoPandas · Shapely 2 · H3 · DuckDB(spatial+vss) / PostgreSQL+PostGIS+pgvector ｜
scikit-learn RandomForest · joblib ｜ fastembed MiniLM (local ONNX) ｜
Gemini (optional, 4-provider cooldown failover) ｜ networkx road-graph routing
