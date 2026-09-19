# PS-2 Final Technical Architecture & Implementation Plan
## GeoReady-AI — AI-Powered GeoSpatial Site Readiness Analyzer

> **Status:** Final architecture for Bit N Build '26 PS-2  
> **Primary goal:** Build a working geospatial site-readiness decision-support platform with deterministic scoring, interactive maps, hotspot analysis, accessibility analysis, RAG, and explainable AI.

---

## 1. Executive Summary

GeoReady-AI helps an analyst decide **where a new facility should be considered** by combining multiple geospatial factors into a configurable **Site Readiness Score (0–100)**.

The system is designed for use cases such as:

- EV charging station
- Retail store
- Warehouse
- Telecom tower
- Service center
- Renewable-energy facility

The application combines:

1. Geospatial data ingestion
2. PostGIS / GeoPandas spatial analysis
3. Configurable weighted scoring
4. Distance-based influence
5. Competitive-density analysis
6. Land-use suitability
7. Environmental-risk analysis
8. H3-based spatial aggregation / hotspot visualization
9. Routing / catchment analysis
10. Interactive map visualization
11. RAG-based contextual knowledge retrieval
12. LLM-generated explanations
13. Site comparison
14. Report export

### Core architecture principle

> **The geospatial engine calculates facts and scores. The LLM explains those facts.**

Do not use an LLM to calculate population, distances, competitor counts, scores, H3 cells, or routes.

---

# 2. Final Technology Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- MapLibre GL JS
- Recharts

## Backend

- Python
- FastAPI
- GeoPandas
- Shapely
- NumPy
- Pandas
- scikit-learn
- H3

## Database

- PostgreSQL
- PostGIS
- pgvector

## Mapping

- MapLibre GL JS
- OpenFreeMap for the base map

OpenFreeMap currently provides an open OSM-derived map service with no registration or API key for its public instance. It states that the public instance has no stated request/view limit. Always follow the provider's current usage and attribution requirements.

## Routing

Primary:

- OSRM

Alternative:

- Valhalla

## RAG

- PostgreSQL + pgvector
- Sentence Transformers
- Hugging Face embedding models

## LLM

Primary:

- Gemini Flash-class model

Backup:

- Another legitimately available LLM provider/project

## Cache

- PostgreSQL initially
- Redis optionally

---

# 3. Important Clarification: Hugging Face Embeddings

The following are valid Hugging Face Sentence Transformers models:

- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/all-mpnet-base-v2`

They are **model checkpoints**, not unlimited "Hugging Face embedding APIs".

### Local usage

You can use:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

embeddings = model.encode(
    ["Example document"]
)
```

On the first run, the model weights are normally downloaded from Hugging Face and cached locally. After that, embeddings can be generated locally without an embedding API request.

This is the recommended approach for the hackathon.

### Why local embeddings are preferred

- No embedding API quota at runtime
- No embedding API latency
- No per-request external billing
- Works offline after the model is available
- Easy to integrate with pgvector

Hugging Face's current hosted Inference Providers free allowance is only a small monthly credit allocation for Free users, so relying on hosted inference for every embedding request is not the preferred design for this project.

---

# 4. Embedding Model Selection

## Option A — all-MiniLM-L6-v2

```text
Model:
sentence-transformers/all-MiniLM-L6-v2

Embedding dimension:
384

Parameters:
~22.7M

Primary advantage:
Fast and lightweight

Best use:
Hackathon RAG / local CPU inference
```

Sentence Transformers currently describes `all-MiniLM-L6-v2` as around 5× faster than `all-mpnet-base-v2` while still providing good quality.

## Option B — all-mpnet-base-v2

```text
Model:
sentence-transformers/all-mpnet-base-v2

Embedding dimension:
768

Primary advantage:
Higher embedding quality

Best use:
When retrieval quality matters more than CPU/memory usage
```

Sentence Transformers currently describes `all-mpnet-base-v2` as its higher-quality general-purpose model in this family.

### Important

Do not mix 384-dimensional and 768-dimensional embeddings in the same vector index.

Choose one embedding dimension for the active RAG collection.

### Recommended final choice

Start with:

```text
all-MiniLM-L6-v2
```

Use:

```text
all-mpnet-base-v2
```

as an optional benchmark/upgrade if retrieval quality is not good enough.

---

# 5. Why RAG Is Useful for PS-2

RAG should provide **context**, not geographic computation.

## Good RAG content

Store:

- Business-type rules
- Land-use definitions
- Environmental-risk definitions
- Scoring methodology
- Distance-decay methodology
- Dataset descriptions
- Data-source notes
- Analytical assumptions
- Facility-specific suitability rules
- Explanation templates / guidance
- Definitions of hotspot, catchment, competitor density, etc.

## Do NOT use RAG for

- Population calculations
- Competitor counting
- Distance calculations
- Geometry intersections
- H3 calculations
- DBSCAN calculations
- Route calculation
- Numeric score calculation

Those are deterministic backend tasks.

---

# 6. Final AI + RAG Flow

```text
User
 |
 | asks:
 | "Why is Site A suitable?"
 v
FastAPI
 |
 +--> PostGIS / GeoPandas
 |      |
 |      +--> population
 |      +--> accessibility
 |      +--> competitor density
 |      +--> land use
 |      +--> environmental risk
 |      +--> catchment
 |
 +--> Scoring Engine
 |      |
 |      +--> final score
 |      +--> factor scores
 |      +--> reasons
 |      +--> risks
 |
 +--> RAG Retrieval
 |      |
 |      +--> retrieve 3–5 relevant knowledge chunks
 |
 +--> Gemini
        |
        +--> explain only the supplied facts
        |
        v
   Structured JSON response
```

---

# 7. Structured RAG

Use two information sources:

## A. Structured factual context

Produced by the geospatial backend:

```json
{
  "site_id": "SITE_A",
  "business_type": "EV_CHARGING",
  "overall_score": 84,
  "population_score": 91,
  "accessibility_score": 88,
  "competition_score": 74,
  "land_use_score": 86,
  "environment_score": 79,
  "nearby_competitors": 3,
  "nearest_major_road_km": 0.8,
  "risk_level": "moderate"
}
```

## B. Retrieved RAG context

Example:

```text
EV charging facilities generally benefit from good road
accessibility and demand concentration.

Commercial and mixed-use land may be suitable depending on
local planning constraints.

High environmental risk can reduce site suitability.
```

The LLM receives both.

---

# 8. Token-Minimizing RAG Strategy

Use:

```text
Top-K retrieval:
3–5 chunks

LLM output:
150–300 tokens preferred

Structured site input:
~300–700 tokens

RAG context:
~500–1500 tokens

System instructions:
~300–500 tokens
```

Target a typical request of roughly:

```text
1.1K–3K input tokens
+
150–300 output tokens
```

Exact token counts will depend on your actual prompts/data.

### Cache AI explanations

Cache using a key containing:

```text
site_id
business_type
weights
scoring_version
retrieval_version
prompt_version
```

Example:

```text
EV_CHARGER_SITE_A_25_25_20_15_15_score_v1_prompt_v2
```

Same request:

```text
Cache hit
    ->
0 LLM calls
```

---

# 9. LLM Usage Rules

## LLM = allowed

- Site explanation
- Why a score is high/low
- Strengths
- Risks
- Plain-language summary
- Business-specific narrative
- Multi-site natural-language comparison
- Report summary

## LLM = not required

- Map interactions
- Layer toggle
- Score calculation
- Population analysis
- Spatial filtering
- Competitor counting
- Hotspot generation
- H3
- DBSCAN
- Distance calculations
- Routing
- Catchment polygon generation

---

# 10. Gemini Multi-Project Failover

The team may configure up to four legitimately available Gemini projects/credentials.

### Important quota rule

Gemini documents that rate limits are applied **per project, not per API key**. Actual RPM, TPM, and RPD limits depend on the model and project tier and must be checked in the Google AI Studio rate-limit view.

Therefore:

> Do not assume that four API keys automatically create four independent quotas.

The failover system should work at the **provider/project credential** level.

### Example configuration

```env
GEMINI_PROVIDER_1_API_KEY=...
GEMINI_PROVIDER_2_API_KEY=...
GEMINI_PROVIDER_3_API_KEY=...
GEMINI_PROVIDER_4_API_KEY=...
GEMINI_MODEL=...
MAX_LLM_ATTEMPTS=4
```

Never commit these values to GitHub.

---

# 11. Automatic LLM Failover Design

## Request flow

```text
AI request
   |
   v
Provider 1
   |
   +--> success -> return result
   |
   +--> temporary failure
            |
            v
        Provider 2
            |
            +--> success
            |
            +--> temporary failure
                     |
                     v
                  Provider 3
                     |
                     v
                  Provider 4
```

## Temporary failures that may trigger failover

Examples:

```text
429 RESOURCE_EXHAUSTED
rate-limit error
temporary timeout
selected 5xx server error
```

## Errors that should NOT be blindly retried

Examples:

```text
400 invalid request
401 invalid credential
403 permission / access problem
malformed request
invalid model name
```

These should mark the provider as unhealthy/configuration-error rather than repeatedly retrying.

---

# 12. Failover State

Maintain:

```text
provider_id
enabled
failure_count
last_failure_time
cooldown_until
last_error
```

Example:

```json
{
  "provider_id": "gemini_1",
  "enabled": true,
  "failure_count": 2,
  "cooldown_until": "2026-09-19T10:20:00Z"
}
```

When a provider receives repeated temporary failures:

```text
Provider 1
   ->
temporarily cooldown
   ->
Provider 2
```

When cooldown ends:

```text
Provider 1
   ->
test request / normal rotation
```

---

# 13. Retry Policy

Use exponential backoff.

Example:

```text
attempt 1:
short delay

attempt 2:
2 × delay

attempt 3:
4 × delay
```

Do not retry indefinitely.

Recommended:

```text
MAX_ATTEMPTS = 4
```

That means at most:

```text
Provider 1
Provider 2
Provider 3
Provider 4
```

for one AI operation, subject to the error policy above.

---

# 14. Gemini Request Capacity Planning

Google currently documents three major interactive dimensions:

- RPM — requests per minute
- TPM — input tokens per minute
- RPD — requests per day

The exact limits vary by model and project/tier and are not guaranteed. The active limits shown in Google AI Studio should be treated as authoritative.

Therefore this project should **not hard-code one internet-found RPM/RPD number**.

Instead implement:

```env
GEMINI_ASSUMED_RPM=10
GEMINI_ASSUMED_RPD=200
GEMINI_ASSUMED_TPM=...
```

as configurable planning values.

Then adjust these values after checking each real project.

---

# 15. Practical Request Budget for the Hackathon

Because the geospatial engine is deterministic, LLM usage can stay small.

## Normal demo

```text
~50–150 LLM calls/day
```

## Heavy demo

```text
~200–400 LLM calls/day
```

## Stress scenario

```text
~500–1000 LLM calls/day
```

These are **application planning scenarios**, not provider quotas.

With caching, actual LLM requests can be much lower.

---

# 16. Maximum AI Calls Per User Operation

## Site calculation

```text
LLM:
0
```

## Site calculation + explanation

```text
LLM:
1
```

## Compare three sites + AI summary

```text
LLM:
1
```

## Generate complete AI report

```text
LLM:
1
```

Avoid making separate LLM calls for each score component.

---

# 17. Example: Bad vs Good Architecture

## Bad

```text
User
 ->
LLM calculates population
 ->
LLM calculates competitors
 ->
LLM calculates road score
 ->
LLM calculates risk
 ->
LLM calculates final score
 ->
LLM explains
```

Problems:

- Expensive
- Slow
- Non-deterministic
- Hard to verify
- More token usage

## Good

```text
PostGIS / GeoPandas
 ->
all spatial calculations
 ->
deterministic score
 ->
RAG
 ->
one LLM call
 ->
explanation
```

---

# 18. Map Architecture

You do not need Google Maps just to display the PS-2 map.

Recommended:

```text
React
  |
  v
MapLibre GL JS
  |
  +--> OpenFreeMap base tiles
  |
  +--> GeoReady custom GeoJSON/vector layers
```

OpenFreeMap currently states that its public instance requires no registration or API key.

### Base map

Use:

```text
OpenFreeMap
```

### Overlay layers

Your backend provides:

```text
population
roads
competitors
land use
risk
candidate sites
H3 readiness cells
catchments
```

---

# 19. Synthetic vs Real Map

Do not build a completely synthetic fake map unless necessary.

Recommended:

```text
Real geographic base map
+
real or public geospatial layers where practical
+
synthetic competitor/candidate/risk data where needed
```

This gives a realistic demo while keeping data preparation manageable.

---

# 20. Routing

For:

```text
10-minute catchment
20-minute catchment
30-minute catchment
```

use:

```text
OSRM
```

or:

```text
Valhalla
```

The system can calculate reachable areas and then intersect those areas with population data.

For the MVP, an approximate distance-based catchment can be used as a fallback, but label it clearly as an approximation.

---

# 21. Geospatial Data Layers

The minimum MVP should contain at least five layers:

```text
1. population.geojson
2. roads.geojson
3. competitors.geojson
4. landuse.geojson
5. risk.geojson
```

Optional:

```text
6. hospitals.geojson
7. schools.geojson
8. parking.geojson
9. transit.geojson
10. utilities.geojson
```

---

# 22. Recommended Data Strategy

For one metropolitan area:

```text
OpenStreetMap
+
public geographic datasets
+
synthetic datasets
```

Do not spend most of the hackathon collecting perfect data.

The scoring pipeline should be designed so sources can later be replaced.

---

# 23. Example Population Layer

```json
{
  "type": "Feature",
  "properties": {
    "population": 12500,
    "density": 5300
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": []
  }
}
```

---

# 24. Example Competitor Layer

```json
{
  "type": "Feature",
  "properties": {
    "name": "Competitor A",
    "category": "EV_CHARGER"
  },
  "geometry": {
    "type": "Point",
    "coordinates": [70.8022, 22.3039]
  }
}
```

---

# 25. Land-Use Layer

Example categories:

```text
commercial
mixed_use
industrial
residential
agricultural
protected
unknown
```

Example suitability mapping:

```text
commercial   -> 100
mixed_use    -> 90
industrial   -> 70
residential  -> 50
agricultural -> 20
protected    -> 0
```

These are application examples, not universal legal standards.

---

# 26. Environmental Risk Layer

Example risk mapping:

```text
low       -> 100
medium    -> 60
high      -> 20
critical  -> 0
```

Again, the actual mapping should be configurable according to the project's methodology and dataset.

---

# 27. Site Readiness Score

All factor scores should be normalized to:

```text
0–100
```

Example weights:

```text
Population         25%
Accessibility      25%
Competition        20%
Land Use           15%
Environment        15%
```

Weights must satisfy:

```text
sum(weights) = 100%
```

---

# 28. Final Score Formula

```text
Final Score =
    Population Score    × Population Weight
  + Accessibility Score × Accessibility Weight
  + Competition Score   × Competition Weight
  + Land Use Score      × Land Use Weight
  + Environment Score   × Environment Weight
```

Example:

```text
Population      = 90
Accessibility   = 85
Competition     = 75
Land Use        = 95
Environment     = 80
```

Weights:

```text
0.25
0.25
0.20
0.15
0.15
```

Result:

```text
90×0.25
+85×0.25
+75×0.20
+95×0.15
+80×0.15

= 85
```

---

# 29. Distance Normalization

For a metric where higher is better:

```text
normalized =
100 × (x - min) / (max - min)
```

For a metric where lower is better:

```text
normalized =
100 × (max - x) / (max - min)
```

Always define sensible min/max ranges.

---

# 30. Distance Decay

Nearby features should have greater influence than distant features.

Possible formula:

```text
influence = exp(-distance / decay_constant)
```

Example:

```text
distance = 1 km
decay_constant = 2

influence ≈ 0.61
```

Use distance decay only where it is analytically justified.

---

# 31. Hard Constraints

Some rules should invalidate a site instead of merely lowering its score.

Examples:

```text
Protected land
        ->
NOT SUITABLE
```

```text
Critical environmental risk
        ->
NOT SUITABLE
```

The backend should distinguish:

```text
soft penalty
```

from:

```text
hard constraint
```

---

# 32. Competition Scoring

Useful metrics:

```text
nearest competitor distance
competitors within 1 km
competitors within 3 km
competitor density
```

A simple competition score may decrease as competitor density increases.

But the behavior should be configurable because the right interpretation depends on the business type.

---

# 33. H3 Analysis

Use H3 to divide the study area into hexagonal analysis cells.

Each cell can store:

```text
cell_id
population
competitor_density
road_accessibility
land_use_score
environment_score
readiness_score
```

Example:

```text
H3 Cell A
Population = 8500
Competitors = 2
Road Score = 81
Risk = Low
Readiness = 86
```

Render the cells as a heatmap.

---

# 34. Hotspot Analysis

Recommended MVP:

```text
H3 aggregation
+
readiness score
+
optional DBSCAN clustering
```

Possible visualization:

```text
0–20    Low
21–40   Weak
41–60   Medium
61–80   Good
81–100  High
```

These are visualization categories, not universal standards.

---

# 35. Catchment Analysis

User selects:

```text
Site A
```

System calculates:

```text
10-minute reachable population
20-minute reachable population
30-minute reachable population
```

Example:

```text
10 min -> 12,400
20 min -> 38,700
30 min -> 72,100
```

Then display the catchment geometry on the map.

---

# 36. Custom Polygon Analysis

Allow the analyst to draw a polygon.

Pipeline:

```text
Draw polygon
   ->
find intersecting layers
   ->
aggregate metrics
   ->
calculate readiness
   ->
display result
```

---

# 37. Site Comparison

Allow 2–3 sites.

Example:

| Factor | Site A | Site B | Site C |
|---|---:|---:|---:|
| Population | 91 | 77 | 84 |
| Accessibility | 88 | 93 | 72 |
| Competition | 74 | 61 | 86 |
| Land Use | 86 | 91 | 80 |
| Environment | 79 | 72 | 95 |
| Overall | 84 | 79 | 84 |

Do not present the table as an absolute truth; display the underlying factors and assumptions.

---

# 38. AI Explanation Contract

The LLM must follow these rules:

```text
1. Use only supplied factual values.
2. Do not invent geographic facts.
3. Do not change the numerical score.
4. Explain strengths.
5. Explain limitations.
6. Mention missing data when relevant.
7. Use concise language.
8. Return structured JSON.
```

---

# 39. Example LLM Output

```json
{
  "summary": "The site has strong overall potential because of high nearby population and good road accessibility.",
  "strengths": [
    "High population score",
    "Strong accessibility"
  ],
  "risks": [
    "Moderate environmental exposure",
    "Moderate competition"
  ],
  "key_reason": "Demand and accessibility are strong, while environmental risk is the main limiting factor."
}
```

---

# 40. Database Schema

## sites

```sql
id
name
latitude
longitude
business_type
created_at
```

## competitors

```sql
id
name
category
geometry
```

## roads

```sql
id
road_type
geometry
```

## population_areas

```sql
id
population
density
geometry
```

## land_use

```sql
id
category
geometry
```

## environmental_risk

```sql
id
risk_type
risk_level
geometry
```

## analysis_results

```sql
id
site_id
population_score
accessibility_score
competition_score
land_use_score
environment_score
overall_score
created_at
```

## rag_documents

```sql
id
title
content
source
metadata
created_at
```

## rag_chunks

```sql
id
document_id
chunk_text
embedding
metadata
created_at
```

For pgvector:

```text
embedding VECTOR(384)
```

if using MiniLM, or:

```text
embedding VECTOR(768)
```

if using MPNet.

---

# 41. Spatial Indexes

Use PostGIS spatial indexes.

Example:

```sql
CREATE INDEX competitors_geom_idx
ON competitors
USING GIST (geometry);
```

Create appropriate indexes for all large spatial tables.

---

# 42. Example Spatial Query

Find competitors inside a radius.

Use PostGIS geography or an appropriate projected CRS for distance calculations.

Conceptually:

```sql
SELECT *
FROM competitors
WHERE ST_DWithin(
    geometry,
    target_geometry,
    distance
);
```

The exact SQL should match the geometry/geography type and units used by the database.

---

# 43. Backend API

## Health

```http
GET /api/health
```

## Layers

```http
GET /api/layers
```

## Sites

```http
GET /api/sites
```

## Create Site

```http
POST /api/sites
```

Example:

```json
{
  "name": "Candidate Site A",
  "latitude": 22.3039,
  "longitude": 70.8022,
  "business_type": "EV_CHARGING"
}
```

## Analyze Site

```http
POST /api/analyze
```

Example:

```json
{
  "latitude": 22.3039,
  "longitude": 70.8022,
  "business_type": "EV_CHARGING",
  "weights": {
    "population": 0.25,
    "accessibility": 0.25,
    "competition": 0.20,
    "land_use": 0.15,
    "environment": 0.15
  }
}
```

## Compare Sites

```http
POST /api/compare
```

## Hotspots

```http
POST /api/hotspots
```

## Catchment

```http
POST /api/catchment
```

## AI Explanation

```http
POST /api/explain
```

## Report

```http
POST /api/report
```

---

# 44. Backend Service Structure

Recommended:

```text
backend/
└── app/
    ├── main.py
    ├── api/
    │   ├── sites.py
    │   ├── analysis.py
    │   ├── hotspots.py
    │   ├── catchment.py
    │   ├── explain.py
    │   └── reports.py
    │
    ├── models/
    ├── schemas/
    │
    ├── geospatial/
    │   ├── loaders.py
    │   ├── distances.py
    │   ├── spatial_queries.py
    │   ├── h3_service.py
    │   └── routing.py
    │
    ├── scoring/
    │   ├── population.py
    │   ├── accessibility.py
    │   ├── competition.py
    │   ├── landuse.py
    │   ├── environment.py
    │   └── engine.py
    │
    ├── rag/
    │   ├── embeddings.py
    │   ├── ingest.py
    │   ├── retriever.py
    │   └── prompts.py
    │
    ├── ai/
    │   ├── gemini_provider.py
    │   ├── provider_manager.py
    │   ├── schemas.py
    │   └── cache.py
    │
    └── config.py
```

---

# 45. Frontend Structure

```text
frontend/
└── src/
    ├── components/
    │   ├── Map/
    │   ├── LayerControl/
    │   ├── ScoreCard/
    │   ├── WeightControls/
    │   ├── SitePanel/
    │   ├── ComparePanel/
    │   ├── CatchmentPanel/
    │   └── AIExplanation/
    │
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── MapAnalysis.tsx
    │   ├── Compare.tsx
    │   └── Analytics.tsx
    │
    ├── services/
    │   └── api.ts
    │
    ├── types/
    └── hooks/
```

---

# 46. Final Repository Structure

```text
GeoReady-AI/
│
├── README.md
├── PROJECT_PLAN.md
├── PS2_TECHNICAL_ARCHITECTURE.md
├── .gitignore
│
├── frontend/
├── backend/
├── data/
│   ├── population.geojson
│   ├── roads.geojson
│   ├── competitors.geojson
│   ├── landuse.geojson
│   └── risk.geojson
│
├── scripts/
│   ├── preprocess.py
│   ├── generate_data.py
│   └── seed_database.py
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── methodology.md
│   └── rag.md
│
└── tests/
    ├── backend/
    └── frontend/
```

---

# 47. Environment Variables

Example:

```env
# Database
DATABASE_URL=postgresql://...

# Primary / backup Gemini projects
GEMINI_PROVIDER_1_API_KEY=
GEMINI_PROVIDER_2_API_KEY=
GEMINI_PROVIDER_3_API_KEY=
GEMINI_PROVIDER_4_API_KEY=

GEMINI_MODEL=

# Routing
OSRM_BASE_URL=

# RAG
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Application limits
MAX_LLM_ATTEMPTS=4
LLM_MAX_OUTPUT_TOKENS=400

# Optional
REDIS_URL=
```

Never commit a populated `.env` file.

Create:

```text
.env.example
```

with placeholders.

---

# 48. GitHub Security

Because the repository is public:

Never commit:

```text
API keys
tokens
passwords
database credentials
private service URLs
production secrets
```

Before pushing:

```bash
git status
git diff
```

Check the repository history if a secret was accidentally committed.

If a real key is exposed, revoke/rotate it immediately.

---

# 49. Development Sequence

Build in this order.

## Phase 1 — Repository

```text
1. Create directories
2. Create README
3. Create .env.example
4. Create backend
5. Create frontend
```

## Phase 2 — Backend foundation

```text
1. FastAPI
2. /api/health
3. Database connection
4. PostGIS setup
```

## Phase 3 — Data

```text
1. Prepare five datasets
2. Validate CRS
3. Validate geometries
4. Load PostGIS
```

## Phase 4 — Scoring

```text
1. Population score
2. Accessibility score
3. Competition score
4. Land-use score
5. Environmental score
6. Final weighted score
```

## Phase 5 — Map

```text
1. Base map
2. Layer loading
3. Layer toggles
4. Candidate markers
5. Site selection
```

## Phase 6 — Analysis

```text
1. Site details
2. Score breakdown
3. Weight controls
4. Comparison
```

## Phase 7 — Hotspots

```text
1. H3 cells
2. readiness score per cell
3. heatmap
4. optional DBSCAN
```

## Phase 8 — Catchment

```text
1. OSRM / fallback
2. 10-minute
3. 20-minute
4. 30-minute
5. population aggregation
```

## Phase 9 — RAG

```text
1. Write knowledge documents
2. Chunk
3. Embed
4. Store vectors
5. Retrieve top-K
```

## Phase 10 — LLM

```text
1. Gemini client
2. provider manager
3. retries
4. cooldown
5. structured JSON output
6. caching
```

## Phase 11 — Reports

```text
1. analysis result
2. map snapshot
3. factor scores
4. AI explanation
5. export
```

## Phase 12 — Deployment

```text
1. frontend deployment
2. backend deployment
3. database
4. environment variables
5. test public demo
```

---

# 50. Team Division

## 4-person team

### Member 1
Frontend + Map

```text
React
MapLibre
Layer controls
Dashboard
Charts
Site UI
```

### Member 2
Backend + Database

```text
FastAPI
PostgreSQL
PostGIS
API
Data ingestion
```

### Member 3
Geospatial + Scoring

```text
GeoPandas
Shapely
H3
DBSCAN
Distance calculations
Scoring engine
```

### Member 4
RAG + AI + Integration

```text
Sentence Transformers
pgvector
Gemini
Provider failover
Caching
AI explanation
Integration/testing
```

---

# 51. Two-Person Version

### Person 1

```text
Frontend
Map
Dashboard
Integration
```

### Person 2

```text
Backend
PostGIS
Scoring
H3
RAG
AI
```

---

# 52. Testing

## Scoring tests

Test:

```text
normal values
minimum values
maximum values
weight changes
invalid weights
hard constraints
missing data
```

## Spatial tests

Test:

```text
point in polygon
distance calculation
competitor radius
H3 conversion
geometry validity
```

## API tests

Test:

```text
GET /health
GET /layers
POST /analyze
POST /compare
POST /hotspots
POST /catchment
POST /explain
```

## AI tests

Test:

```text
successful provider
429
timeout
5xx
invalid credentials
all providers unavailable
malformed AI output
```

---

# 53. AI Failover Error Handling

Expected behavior:

```text
Request
  |
  +--> Provider 1 success
  |       -> return
  |
  +--> Provider 1 429
  |       -> cooldown
  |       -> Provider 2
  |
  +--> Provider 1 timeout
  |       -> Provider 2
  |
  +--> Provider 1 401
  |       -> mark unhealthy
  |       -> Provider 2
  |
  +--> all providers fail
          -> return controlled fallback
```

Controlled fallback example:

```json
{
  "success": false,
  "type": "AI_TEMPORARILY_UNAVAILABLE",
  "message": "The geospatial analysis is complete, but the AI explanation service is temporarily unavailable."
}
```

The underlying score must still be displayed.

This is important:

> **AI failure must never break the geospatial analysis.**

---

# 54. Graceful AI Degradation

If all LLM providers fail, the application should still display:

```text
Overall score
Factor scores
Reasons generated from deterministic rules
Risks
Metrics
```

Example deterministic explanation:

```text
Overall readiness is 84/100.

Strengths:
- Population score: 91
- Accessibility score: 88
- Land-use score: 86

Limitations:
- Competition score: 74
- Environmental score: 79
```

Then:

```text
AI explanation unavailable
```

can be shown as a small status message.

---

# 55. Caching Strategy

Cache:

```text
site analysis
hotspot result
catchment result
AI explanation
RAG retrieval results
```

Invalidate cache when:

```text
weights change
data changes
scoring version changes
prompt version changes
RAG knowledge changes
```

---

# 56. Business-Type Weight Presets

Example EV charger:

```text
Population        20%
Accessibility     35%
Competition       20%
Land Use          10%
Environment       15%
```

Example retail:

```text
Population        30%
Accessibility     25%
Competition       20%
Land Use          15%
Environment       10%
```

Example warehouse:

```text
Population         5%
Accessibility      30%
Competition         5%
Land Use            30%
Environment         15%
Utilities           15%
```

These are configurable examples and not universal business rules.

---

# 57. Demo Scenario

Use one simple business use case.

Recommended:

```text
Business:
EV Charging Station

Study Area:
One metropolitan area
```

### Demo

```text
1. Open dashboard
2. Display map
3. Turn on five layers
4. Enable readiness heatmap
5. Click candidate Site A
6. Show 0–100 score
7. Show factor breakdown
8. Show competitors
9. Show nearby road access
10. Show 10/20/30 minute catchment
11. Change weights
12. Score changes
13. Compare Site A/B/C
14. Ask AI why Site A scored highly
15. Show RAG-assisted explanation
16. Generate report
```

---

# 58. Example Final Result

```text
SITE A

Overall Readiness
84 / 100

Population
91

Accessibility
88

Competition
74

Land Use
86

Environment
79

Catchment:
10 min -> 12.4K
20 min -> 38.7K
30 min -> 72.1K

Nearby competitors:
3

Nearest major road:
0.8 km

Risk:
Moderate

AI Summary:
"Strong demand and accessibility drive the site's high score.
Moderate competition and environmental exposure reduce the result."
```

---

# 59. MVP Definition

The project is MVP-complete when all of the following work:

```text
[ ] Interactive map
[ ] Five geospatial layers
[ ] Candidate location selection
[ ] 0–100 readiness score
[ ] Configurable weights
[ ] Score breakdown
[ ] Competition analysis
[ ] Land-use suitability
[ ] Environmental risk
[ ] Readiness heatmap
[ ] H3 aggregation
[ ] Site comparison
[ ] AI explanation
[ ] RAG retrieval
```

---

# 60. Advanced Features — Only After MVP

```text
[ ] OSRM isochrones
[ ] Custom polygon analysis
[ ] Advanced DBSCAN / Gi*
[ ] PDF export
[ ] Real-time data
[ ] Multiple cities
[ ] Authentication
[ ] Cloud deployment
[ ] Admin data ingestion
```

Do not delay the core demo for these features.

---

# 61. Final Architecture Diagram

```text
                              USER
                                |
                                v
                     +--------------------+
                     |   React Frontend   |
                     |  TypeScript/Tailwind|
                     +----------+---------+
                                |
                                v
                     +--------------------+
                     |    MapLibre GL     |
                     +----------+---------+
                                |
                    +-----------+-----------+
                    |                       |
                    v                       v
              OpenFreeMap            GeoReady Layers
              Base Map               GeoJSON / API
                                            |
                                            v
                                 +---------------------+
                                 |       FastAPI       |
                                 +----------+----------+
                                            |
             +------------------------------+------------------------------+
             |                              |                              |
             v                              v                              v
       +------------+                 +------------+                 +------------+
       |   PostGIS  |                 | GeoPandas  |                 |   OSRM     |
       | spatial DB |                 | processing |                 |  routing   |
       +------+-----+                 +------+-----+                 +------+-----+
              |                              |                              |
              +---------------+--------------+------------------------------+
                              |
                              v
                     +--------------------+
                     |   Scoring Engine   |
                     |   deterministic    |
                     +----------+---------+
                                |
                                v
                    +----------------------+
                    | Structured Site Data |
                    +----------+-----------+
                               |
                      +--------+--------+
                      |                 |
                      v                 v
                +-----------+     +-------------+
                | pgvector  |     | AI Provider |
                |   RAG     |     |   Manager   |
                +-----+-----+     +------+------+ 
                      |                    |
                      |                    +--> Gemini Project 1
                      |                    +--> Gemini Project 2
                      |                    +--> Gemini Project 3
                      |                    +--> Gemini Project 4
                      |                    |
                      +---------+----------+
                                |
                                v
                       AI Explanation JSON
                                |
                                v
                         React UI / Report
```

---

# 62. Architectural Rules

These rules should not be broken without a clear reason.

### Rule 1
The LLM does not calculate the numerical score.

### Rule 2
PostGIS/GeoPandas is the source of truth for geographic calculations.

### Rule 3
RAG provides contextual knowledge, not geographic measurements.

### Rule 4
AI failure must not break the core application.

### Rule 5
API keys must stay server-side.

### Rule 6
Public GitHub must never contain secrets.

### Rule 7
Cache repeated AI requests.

### Rule 8
Keep LLM prompts compact.

### Rule 9
Use structured JSON from the LLM.

### Rule 10
Every score should be reproducible from data + weights + methodology.

---

# 63. Final Project Flow

```text
DATA
  |
  v
INGESTION
  |
  v
POSTGIS / GEOPANDAS
  |
  v
SPATIAL ANALYSIS
  |
  +--> population
  +--> roads
  +--> competitors
  +--> land use
  +--> environmental risk
  +--> catchment
  |
  v
SCORING ENGINE
  |
  v
0–100 SITE READINESS
  |
  +--> heatmap
  +--> comparison
  +--> analytics
  |
  v
RAG
  |
  v
GEMINI
  |
  v
EXPLAINABLE AI
```

---

# 64. Final Technical Recommendation

## Use this exact combination for the MVP

```text
Frontend
React + TypeScript + Tailwind + MapLibre

Base Map
OpenFreeMap

Backend
FastAPI

Database
PostgreSQL + PostGIS + pgvector

Geospatial
GeoPandas + Shapely + H3 + scikit-learn

Routing
OSRM

Embeddings
sentence-transformers/all-MiniLM-L6-v2 locally

Optional higher-quality embedding benchmark
sentence-transformers/all-mpnet-base-v2

LLM
Gemini Flash-class

LLM failover
Up to four separately authorized Gemini projects/credentials,
with cooldown + retry + graceful fallback

Cache
PostgreSQL initially, Redis optional

Deployment
Any suitable frontend + Python backend hosting
```

---

# 65. Why This Architecture Fits PS-2

The architecture directly addresses the main PS-2 capabilities:

```text
5+ geospatial layers
        -> YES

0–100 configurable Site Readiness Score
        -> YES

Distance decay
        -> YES

Competitive density
        -> YES

Threshold constraints
        -> YES

Hotspots / clustering
        -> YES

Interactive map
        -> YES

Layer opacity/toggle
        -> YES

Custom polygons
        -> YES

Site comparison
        -> YES

10/20/30 minute accessibility
        -> YES

AI explanation
        -> YES

RAG
        -> YES

Low LLM usage
        -> YES

Automatic temporary-provider failover
        -> YES

Graceful degradation if all AI providers fail
        -> YES
```

---

# 66. Final One-Line Project Description

> **GeoReady-AI is an AI-assisted geospatial decision-support platform that combines demographic, transportation, competition, land-use, and environmental data to score, compare, visualize, and explain candidate locations for new facilities.**

---

# 67. Sources / Current Provider Notes

The following current documentation was checked when this architecture was finalized:

1. Google Gemini API rate limits:
   https://ai.google.dev/gemini-api/docs/rate-limits

2. Hugging Face Inference Providers pricing:
   https://huggingface.co/docs/inference-providers/en/pricing

3. Hugging Face `all-MiniLM-L6-v2`:
   https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

4. Hugging Face `all-mpnet-base-v2`:
   https://huggingface.co/sentence-transformers/all-mpnet-base-v2

5. Sentence Transformers pretrained model documentation:
   https://www.sbert.net/docs/sentence_transformer/pretrained_models.html

6. OpenFreeMap:
   https://openfreemap.org/

Provider quotas, pricing, and service policies can change. For actual Gemini RPM/TPM/RPD values, use the limits shown for the specific project/model in Google AI Studio at implementation time.
