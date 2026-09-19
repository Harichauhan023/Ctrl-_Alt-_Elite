# 🎤 GeoReady-AI — 8-Minute Judge Demo Script

Scenario: **"Rajkot wants 20 new public EV chargers. Where should the first five go?"**

> Breathe. The app degrades gracefully at every step — there is **no dark path** in this demo.
> If Wi-Fi dies: the map badge flips to `offline-safe basemap` and *everything else keeps working*
> (all data layers are local). If all AI keys die: the explainers and the chat assistant
> silently switch to deterministic mode and *keep answering*. Say that out loud — judges remember it.

---

### 0:00 — The hook (30 s)
> "Choosing where to put an EV charger today is a spreadsheet-and-gut-feeling job. Data exists —
> population, roads, competitors, zoning, flood risk — but it lives in six different silos.
> GeoReady-AI fuses them into ONE reproducible number: a Site Readiness Score. And we built it on
> our own city, Rajkot. It's not a dashboard — it's a **conversation with the map**."

Show **Dashboard** (KPI cards): 9 lakh modelled residents, 1.5k+ km REAL OpenStreetMap roads,
649 analysis zones. *"The road network is real OSM data — 1,538 ways."*

### 0:05 — Chat-first landing (45 s)
> "The product opens as a **conversation**, not a dashboard. Ask: *'is the population data real or
> synthetic?'* — watch the typing answer arrive with its **top-k RAG sources**: real document paths
> from `rag/documents/`, each with a cosine-similarity bar. Then *'recommend top 5 zones for EV
> charging'* — the assistant runs the LIVE engine (649 zones ranked) and its cards jump straight
> onto the map."

Mention: the badge row — **position Postgres+pgvector or DuckDB vss, RandomForest R², MiniLM RAG**.

### 1:15 — The map & layers (40 s)
Go to **Map**. Show the **basemap switcher** (Satellite / Streets / Dark) — "real geographic tiles,
every mode". Toggle layers one by one, naming the factor: Toggle layers one by one, naming the factor:
population (H3 demand grid) → roads (real OSM) → competitors (EV chargers) → land-use → flood risk.
> "Five core factors, three bonus layers — hospitals, schools, fuel."

### 2:00 — Hotspot heatmap (30 s)
Turn on **Readiness heatmap**. Point at the green ridge:
> "Every hexagon ran the SAME scoring engine as a point site — 649 zones, precomputed factors.
> This is the 'where should we even look' answer."

### 2:30 — Just ask: the AI assistant (60 s) ⭐⭐
Open the **Assistant** tab (right dock). Type — don't use the quick prompts:

- **"recommend top 3 zones for ev charging"** →
  > "Watch: the assistant didn't guess — it filtered all 649 zones and ranked them. Pure engine."
  Click the ✈ fly-to chip, then 🎯 analyze — the site panel opens with a full 0–100 analysis.

- **"how is 150ft ring road for ev charging?"** → named-site analysis with a real score.

- **"compare old city vs greenland for retail"** → side-by-side winner with the delta.

- **"what does NOT_SUITABLE mean?"** → knowledge answer with source citations from the RAG corpus.

> "Provider badge up top: run it with a Gemini key and Gemini narrates; unplug every key and the
> deterministic router answers identically. The AI never invents a number — every figure in that
> reply came out of our scoring engine in the background."

### 3:30 — Top-K recommender, by hand (35 s)
Left panel → **Recommend**. Set *min population score 40*, *max rivals within 1 km = 1*,
top 5 → **Run**. Numbered green markers appear on the map.
> "Constraint-first search over every H3 cell in the city — the same math as the chat, hands-on."

### 4:05 — Score a site + **the ML row** (70 s) ⭐⭐
Click a candidate pin. Cover: status chip, gauge, factor bars, metrics grid — then the **violet ML panel**:
> "Same 13 engineered features feed a RandomForest trained on **10,000 synthetic candidate sites**
> with a documented noisy ground-truth rule. Holdout: **MAE 1.85, R² 0.959**. Predictions sit
> side-by-side with the deterministic rules score — this Δ is our independent cross-check.
> Importantly: weight sliders do **not** move the ML number — that's how you know it's not a lookup."
Then move a weight slider — RULES score shifts, ML stays. Then press **Explain** — the AI card shows
its **pipeline trace** (features duckdb ✓ · ML ✓ · RAG 4 chunks · provider) and **RAG sources with
real file paths and similarity bars**. 
Click **Old City Core** marker. Panel shows its score with factor bars.
Walk the metrics: pop within 1 km, nearest major road, competitors, land-use, risk.
> "0–100, weighted sum of five normalized factors. Deterministic — same data, same weights,
> same score. Every time."

### 5:15 — What-if ghost rivals (45 s) ⭐
In the **What-if scenario** box (Analysis tab): **Drop a rival** → click 300 m from the pin.
> "A simulated competitor just entered the market — watch the competition factor collapse
> honestly, live, re-run by the deterministic engine." *(competition score drops visibly;
> the orange 🧪 marker stays until Cleared.)*

### 6:00 — Same pin, six business lenses (20 s)
**Score all business types here** → six bars: retail vs EV vs clinic vs warehouse…
> "One location, six business models, identical engine — that's the generalization story."

### 6:20 — Draw an area (50 s)
**✏ Draw area** (map toolbar) → click 4–5 vertices around a neighbourhood, **Enter** to finish.
The Area tab fills: km², population inside, road km, competitors, readiness band-mix chart,
land-use mix, engineering-style verdict lines.
> "True line∩polygon road length, population by res-9 cell containment — not a bbox estimate."

### 7:10 — Live weights + hard constraints (30 s)
Drag **Accessibility 35 → 15**. Score and heatmap morph together.
Then click inside the **Aji river pocket** near old city: red **⛔ NOT SUITABLE** banner.
> "Some conditions don't lower your score — they end the conversation. Penalties and hard
> constraints are separate, exactly like a planning department."

### 7:40 — Knowledge Explorer: show them the VECTOR STORE (40 s)
Open **Knowledge**: search **"competition distance decay"** — 44 chunks, cosine bars.
> "This is the actual retrieval corpus — methodology deep-dives, six business playbooks,
> Rajkot geography, FAQ. Retrieval grounds the AI; it never computes."

### 8:20 — Close (15 s)
> "Real OSM roads under our feet, a reproducible engine, a chat assistant that actually runs it,
> drawn-area analytics, what-if scenarios — and a demo that survives dead Wi-Fi and dead API keys.
> GeoReady-AI doesn't just answer *where* — it shows *why*."

---

## 🛟 Recovery sheet

| If this breaks… | Do this |
|---|---|
| Base tiles blank | Point at badge: *"offline-safe mode engaged — that's a feature."* All layers are local. |
| Explain/chat spinner hangs | It falls back in ≤20 s; or say *"…and this is the graceful degradation path — deterministic mode."* |
| Chat mis-parses a odd sentence | Rephrase or click a quick prompt — the router is deterministic and forgiving; cite hollow words never matter. |
| Judge asks "why is X scored Y?" | Open factor bars + metrics grid — every number traces to a dataset. |
| Judge challenges synthetic data | README honesty: sources are labelled & replaceable; pipeline ingests municipal GeoJSON with zero code changes. Population is a *model* (~9L ≈ Rajkot urban core). |
| Polygon / recommender slow | They scan 649 cells server-side in <1 s; if there's a hiccup, talk through the method label. |

## ❓ Likely Q&A bank

- **Why in-memory GeoPandas and not PostGIS?** 24-hour build; the store is one swappable class; API contract unchanged. Spatial indexing needs here are trivial at city scale.
- **Is the score reproducible?** Yes — pure functions of data+weights; we have pytest proving determinism and constraints.
- **What stops the LLM from inventing facts?** It receives only engine facts + retrieved chunks and a ≤110-word system prompt; every number in chat replies is computed by the engine first, and the reply template embeds it verbatim.
- **How does competition polarity work?** Per-business: EV avoids clusters; retail inverts (agglomeration validates demand). Ghost rivals flow through the same polarity — dropping one near a retail site can *raise* its score.
- **Is the chat assistant a separate AI?** No — it's an intent router sitting in front of `/api/recommend`, `/api/analyze`, `/api/compare` and the RAG corpus, with a bounded LLM narration step that has a deterministic fallback.
- **Why retrieval but no vector DB?** 44 chunky × 384-dim is a 67 kB matrix; numpy cosine in <10 ms. Right-toolism — the whole research corpus fits in memory and ships with the repo.
