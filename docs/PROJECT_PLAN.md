# GeoReady-AI
## AI-Powered GeoSpatial Site Readiness Analyzer

### 1. Problem Statement

Businesses and organizations often need to decide **where to open or deploy a new facility**, such as:

- Retail store
- Warehouse
- EV charging station
- Telecom tower
- Renewable-energy facility
- Service center

The decision depends on multiple geographic factors:

- Population / demographics
- Roads and transportation accessibility
- Existing competitors
- Land use / zoning
- Environmental risks
- Utilities / infrastructure
- Travel accessibility

Analyzing these factors manually is difficult because the data comes from different sources.

### 2. Our Solution

**GeoReady-AI** is an interactive geospatial decision-support platform that evaluates candidate locations and calculates a **Site Readiness Score from 0 to 100**.

The system combines multiple geographic layers and produces:

1. Site Readiness Score
2. Factor-by-factor score breakdown
3. High-potential and underserved areas
4. Competitive-density analysis
5. Accessibility / catchment analysis
6. Site-to-site comparison
7. AI-generated explanation of why a location is suitable or unsuitable
8. Exportable site analysis report

### 3. Example Use Case

Suppose a company wants to open a new EV charging station.

The company provides:

```text
Business Type: EV Charging Station

Location:
Rajkot Metropolitan Area

Important Factors:
- High population
- Major roads nearby
- Low existing competition
- Low flood risk
- Good accessibility
```

The system analyzes the selected metropolitan area and produces:

```text
Candidate Site: Site A

Overall Site Readiness Score: 84/100

Population Score:       92
Accessibility Score:    89
Competition Score:      76
Land Use Score:         85
Environmental Score:    78

Final Recommendation:
High potential

Main Reasons:
+ High nearby population
+ Excellent road accessibility
+ Low competitor density
+ Suitable land-use conditions

Risk:
- Moderate environmental risk
```

The user can compare Site A with Site B and Site C.

---

# 4. Core PS-2 Requirements

The application should support the following capabilities.

## 4.1 Geospatial Data Ingestion

The system must be able to work with at least **5 geospatial layers**.

Recommended layers:

1. Population / demographics
2. Roads / transportation
3. Competitor locations
4. Land use / zoning
5. Environmental / risk data

Optional layers:

6. Hospitals
7. Schools
8. Parking
9. Public transport
10. Utility infrastructure
11. Commercial areas
12. Administrative boundaries

Supported data formats can include:

- GeoJSON
- Shapefile
- GeoTIFF
- WKT

For the hackathon, GeoJSON is the easiest format for the MVP.

---

# 5. Recommended Technology Stack

## Frontend

```text
React
TypeScript
Tailwind CSS
MapLibre GL JS
Recharts
```

Alternative:

```text
Next.js
```

## Backend

```text
Python
FastAPI
GeoPandas
Shapely
Pandas
NumPy
scikit-learn
H3
```

## Database

Recommended:

```text
PostgreSQL
PostGIS
```

For a very fast MVP, GeoJSON files can temporarily be used before moving to PostGIS.

## Routing

Use one of:

```text
OSRM
Valhalla
```

For the first MVP, road-distance calculations can be approximated using geographic distance if a routing service is not yet integrated.

## Map

Recommended:

```text
MapLibre GL JS
```

Alternative:

```text
Leaflet
```

## AI

Use an LLM only where it adds value:

```text
Gemini / OpenAI / Claude
```

Primary AI use:

- Explain score
- Generate site summary
- Generate business-specific insights
- Explain trade-offs

The core geospatial scoring should be deterministic rather than completely dependent on an LLM.

---

# 6. High-Level Architecture

```text
                 ┌─────────────────────────┐
                 │        User / Analyst   │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │      React Frontend     │
                 │                         │
                 │ - Map                   │
                 │ - Layers                │
                 │ - Score Dashboard       │
                 │ - Site Comparison       │
                 │ - Reports               │
                 └────────────┬────────────┘
                              │ REST / JSON
                              ▼
                 ┌─────────────────────────┐
                 │       FastAPI Backend   │
                 │                         │
                 │ - Site Analysis         │
                 │ - Scoring Engine        │
                 │ - Spatial Analysis      │
                 │ - Route Analysis        │
                 │ - Recommendations       │
                 └────────────┬────────────┘
                              │
             ┌────────────────┼─────────────────┐
             ▼                ▼                 ▼
      ┌────────────┐   ┌─────────────┐   ┌──────────────┐
      │ PostGIS    │   │ GeoSpatial  │   │ AI Service   │
      │ Database   │   │ Processing  │   │ / LLM        │
      └────────────┘   └─────────────┘   └──────────────┘
             │                │
             ▼                ▼
      Population        OSM / Risk /
      Competitors       Land Use / etc.
```

---

# 7. Main Application Modules

The system should be divided into these modules.

## Module 1 — Map

Responsibilities:

- Display geographic map
- Show candidate locations
- Show data layers
- Toggle layers
- Change layer opacity
- Select a location
- Draw custom polygons
- Zoom to analysis area

Example:

```text
[ Population ]       ON
[ Roads ]             ON
[ Competitors ]       ON
[ Land Use ]          ON
[ Flood Risk ]        OFF
```

---

# 8. Geospatial Layers

## 8.1 Population Layer

Purpose:

Identify areas with high potential customer density.

Example GeoJSON:

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

Possible metric:

```text
Population Density = population / area
```

Higher population density generally produces a higher score for a retail-oriented use case.

---

# 9. Road / Transportation Layer

Purpose:

Measure accessibility.

Example:

```text
distance_to_major_road = 0.8 km
road_type = highway
traffic_score = 82
```

Potential score:

```text
Closer to major road
        ↓
Higher accessibility score
```

---

# 10. Competitor Layer

Competitors are represented as points.

Example:

```json
{
  "name": "Competitor A",
  "type": "EV Charger",
  "latitude": 22.3039,
  "longitude": 70.8022
}
```

Useful metrics:

```text
competitors within 1 km
competitors within 3 km
competitor density
distance to nearest competitor
```

A simple competition score can be:

```text
More competitors
      ↓
Lower score
```

However, this should be configurable because some businesses may prefer high commercial activity.

---

# 11. Land Use / Zoning Layer

Example categories:

```text
Commercial
Residential
Industrial
Agricultural
Protected
Mixed Use
Unknown
```

Example suitability mapping:

```text
Commercial      = 100
Mixed Use       = 90
Industrial      = 70
Residential     = 50
Agricultural    = 20
Protected       = 0
```

These values must be configurable based on the selected business type.

---

# 12. Environmental Risk Layer

Possible risks:

- Flood
- Wildfire
- Pollution
- Landslide
- Extreme environmental exposure

Example:

```text
Low Risk       = 100
Medium Risk    = 60
High Risk      = 20
Critical Risk  = 0
```

The score should reduce as risk increases.

---

# 13. Site Readiness Scoring Engine

The scoring engine is the heart of the project.

Every candidate site gets a score:

```text
0 = Very Poor
100 = Excellent
```

Example factors:

```text
Population            25%
Accessibility         25%
Competition           20%
Land Use              15%
Environmental Risk    15%
```

The total weights must equal:

```text
100%
```

---

# 14. Mathematical Scoring Formula

For a candidate location:

```text
Final Score =
    Population Score      × Population Weight
  + Accessibility Score   × Accessibility Weight
  + Competition Score     × Competition Weight
  + Land Use Score        × Land Use Weight
  + Environment Score     × Environment Weight
```

Example:

```text
Population = 90
Accessibility = 85
Competition = 75
Land Use = 95
Environment = 80
```

Weights:

```text
Population = 0.25
Accessibility = 0.25
Competition = 0.20
Land Use = 0.15
Environment = 0.15
```

Calculation:

```text
(90 × 0.25)
+ (85 × 0.25)
+ (75 × 0.20)
+ (95 × 0.15)
+ (80 × 0.15)

= 22.50
+ 21.25
+ 15.00
+ 14.25
+ 12.00

= 85.00
```

Final:

```text
85/100
```

---

# 15. Configurable Weights

The user must be able to change weights.

Example UI:

```text
Population        █████████████ 30%
Accessibility     ██████████    25%
Competition       ████████      20%
Land Use          █████         15%
Environment       ███           10%

                    [Calculate]
```

After changing a weight, the score should update.

Example:

```text
Before:
Site A = 82

Population increased in importance:
Site A = 87
```

This demonstrates that the analyzer is configurable rather than using one fixed formula.

---

# 16. Normalization

Different data sources have different units:

```text
Population = people
Distance = km
Competitors = count
Risk = category
```

These should be normalized to a common range:

```text
0 to 100
```

Example min-max normalization:

```text
normalized =
    100 × (x - min) / (max - min)
```

For metrics where lower is better:

```text
normalized =
    100 × (max - x) / (max - min)
```

Example:

```text
Distance to road:

0 km      → approximately 100
5 km      → approximately 0
```

Use realistic maximum/minimum values for each dataset.

---

# 17. Distance Decay

The effect of a geographic factor usually decreases with distance.

For example:

```text
Population 0.5 km away
    ↓
strong influence

Population 5 km away
    ↓
weak influence
```

A simple exponential distance decay function can be used:

```text
influence = e^(-distance / decay_constant)
```

Example:

```text
distance = 1 km
decay constant = 2

influence ≈ 0.61
```

This allows nearby features to contribute more strongly than distant features.

---

# 18. Threshold Constraints

Some conditions should not merely reduce the score; they can make a location invalid.

Example:

```text
Flood Risk > Critical
        ↓
Site = NOT SUITABLE
```

Other examples:

```text
Distance from road > 5 km
        ↓
Invalid

Land use = Protected
        ↓
Invalid
```

The system should distinguish:

```text
Score penalty
```

from

```text
Hard constraint
```

---

# 19. Site Analysis Pipeline

The complete processing flow:

```text
User selects location
        ↓
Collect geographic features around location
        ↓
Calculate distances
        ↓
Calculate feature densities
        ↓
Normalize values
        ↓
Apply distance decay
        ↓
Apply constraints
        ↓
Calculate factor scores
        ↓
Apply user-selected weights
        ↓
Calculate final score
        ↓
Generate explanation
        ↓
Display result on map
```

---

# 20. Example Candidate Site Input

```json
{
  "site_id": "SITE_001",
  "latitude": 22.3039,
  "longitude": 70.8022,
  "business_type": "EV_CHARGING"
}
```

---

# 21. Example Site Result

```json
{
  "site_id": "SITE_001",
  "overall_score": 84,
  "scores": {
    "population": 91,
    "accessibility": 88,
    "competition": 74,
    "land_use": 86,
    "environment": 79
  },
  "status": "HIGH_POTENTIAL",
  "reasons": [
    "High nearby population",
    "Good access to major roads",
    "Moderate competitor density",
    "Suitable land use"
  ],
  "risks": [
    "Moderate environmental exposure"
  ]
}
```

---

# 22. Spatial Clustering / Hotspot Analysis

The system should identify geographic zones where favorable conditions are concentrated.

Possible techniques:

```text
DBSCAN
H3
Getis-Ord Gi*
```

For the MVP, H3 and DBSCAN are easier to demonstrate.

---

# 23. DBSCAN Example

DBSCAN groups nearby high-value locations.

Example:

```text
Site 1 ●
Site 2 ●
Site 3 ●
Site 4 ●

          Cluster A
```

A cluster could represent:

```text
High population
+ good roads
+ low competition
```

Then display:

```text
High Potential Zone
```

on the map.

---

# 24. H3 Grid Approach

Convert the study area into geographic hexagons.

Each hexagon stores summary information:

```text
H3 Cell
----------------
Population = 8500
Competitors = 2
Road Score = 81
Flood Risk = Low
Readiness Score = 86
```

This makes it easier to generate a heat map.

Example:

```text
       ⬡ ⬡ ⬡ ⬡
     ⬡ ⬡ ⬡ ⬡ ⬡
       ⬡ ⬡ ⬡ ⬡
     ⬡ ⬡ ⬡ ⬡ ⬡

Each hexagon = one geographic analysis unit
```

---

# 25. Heatmap

Display:

```text
High Readiness
     ↓
Hotspot

Low Readiness
     ↓
Coldspot
```

Users should be able to understand the map visually.

---

# 26. Accessibility / Catchment Analysis

The user can select a location and ask:

```text
What population can reach this location
within 10, 20, or 30 minutes?
```

Example:

```text
10-minute catchment
Population = 12,400

20-minute catchment
Population = 38,700

30-minute catchment
Population = 72,100
```

The application can calculate this using:

```text
OSRM / Valhalla
```

or use an approximate distance-based calculation for the MVP.

---

# 27. Isochrone Concept

An isochrone represents an area reachable within a specific travel time.

```text
         30 min
      _____________
    /               \
   /    20 min       \
  /     _________      \
 /     / 10 min  \      \
|     |   SITE    |      |
 \     \_________/      /
  \                   /
   \_________________/
```

The map should allow:

```text
[10 min] [20 min] [30 min]
```

---

# 28. Custom Polygon Analysis

The user should be able to draw an area on the map.

Example:

```text
User draws polygon
        ↓
System finds all data inside polygon
        ↓
Calculate:
- Population
- Competitors
- Roads
- Risk
- Overall readiness
```

This can be useful for analyzing an entire commercial zone.

---

# 29. Compare Sites

Provide a comparison screen.

Example:

| Factor | Site A | Site B | Site C |
|---|---:|---:|---:|
| Population | 91 | 77 | 84 |
| Accessibility | 88 | 93 | 72 |
| Competition | 74 | 61 | 86 |
| Land Use | 86 | 91 | 80 |
| Environment | 79 | 72 | 95 |
| Overall | 84 | 79 | 84 |

The system should allow the user to inspect why scores differ.

---

# 30. Explainable AI

Do not make the LLM responsible for calculating the numerical score.

Instead:

```text
Geospatial Engine
        ↓
calculates actual numbers
        ↓
AI
        ↓
explains the result in natural language
```

Example input to AI:

```json
{
  "overall_score": 84,
  "population_score": 91,
  "accessibility_score": 88,
  "competition_score": 74,
  "land_use_score": 86,
  "environment_score": 79
}
```

AI output:

```text
This site has strong potential mainly because of high nearby
population and good transportation accessibility. Its main
limitation is moderate environmental risk and competition.
```

This is more reliable than asking the LLM to directly decide the score.

---

# 31. Business-Type Configuration

The scoring system should support different use cases.

Example:

## Retail Store

```text
Population        30%
Accessibility     25%
Competition       20%
Land Use          15%
Environment       10%
```

## Warehouse

```text
Population         5%
Accessibility     30%
Competition        5%
Land Use           30%
Environment        15%
Utilities          15%
```

## EV Charger

```text
Population        20%
Accessibility     35%
Competition       20%
Land Use           10%
Environment        15%
```

The weights are examples and should be editable by the user.

---

# 32. Recommended Database Design

## Table: sites

```sql
sites
-----
id
name
latitude
longitude
business_type
created_at
```

## Table: competitors

```sql
competitors
-----------
id
name
category
latitude
longitude
geometry
```

## Table: roads

```sql
roads
-----
id
road_type
geometry
```

## Table: population_areas

```sql
population_areas
----------------
id
population
density
geometry
```

## Table: land_use

```sql
land_use
--------
id
category
geometry
```

## Table: environmental_risk

```sql
environmental_risk
------------------
id
risk_type
risk_level
geometry
```

## Table: analysis_results

```sql
analysis_results
----------------
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

---

# 33. Spatial Database

Use PostGIS for geographic queries.

Example concepts:

```sql
ST_Distance()
ST_Within()
ST_Intersects()
ST_Contains()
ST_Buffer()
```

Example:

Find competitors within 2 km of a candidate site.

```sql
SELECT *
FROM competitors
WHERE ST_DWithin(
    geometry,
    ST_SetSRID(ST_Point(:longitude, :latitude), 4326),
    :distance
);
```

For production-quality geographic distance calculations, use an appropriate projected coordinate system or geography type rather than assuming raw latitude/longitude units are kilometers.

---

# 34. API Design

## Health Check

```http
GET /api/health
```

## Get Map Layers

```http
GET /api/layers
```

## Get Sites

```http
GET /api/sites
```

## Create Site

```http
POST /api/sites
```

Request:

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

Request:

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

## Hotspot Analysis

```http
POST /api/hotspots
```

## Catchment Analysis

```http
POST /api/catchment
```

## Generate AI Explanation

```http
POST /api/explain
```

---

# 35. Frontend Pages

## Page 1 — Dashboard

Show:

```text
Total Sites
High Potential Sites
Average Score
Critical Risk Sites
```

---

## Page 2 — Interactive Map

Main application screen.

Components:

```text
Map
Layer Controls
Search
Business Type
Weight Controls
Candidate Sites
Heatmap
```

---

## Page 3 — Site Analysis

Show:

```text
Site name
Coordinates
Overall score
Score breakdown
Reasons
Risks
Nearby competitors
Accessibility
Population
```

---

## Page 4 — Compare

Show:

```text
Site A
Site B
Site C

Charts + score breakdown
```

---

## Page 5 — Analytics

Show:

```text
Population distribution
Competitor distribution
High-potential zones
Environmental-risk zones
Average site scores
```

---

# 36. Suggested UI Layout

```text
┌──────────────────────────────────────────────────────────┐
│ GeoReady-AI                         Business: EV Charger │
├───────────────┬──────────────────────────────────────────┤
│ Layers        │                                          │
│               │                 MAP                      │
│ ☑ Population  │                                          │
│ ☑ Roads       │          ● Site A                        │
│ ☑ Competitors │                       ● Site B            │
│ ☑ Land Use    │                                          │
│ ☑ Risk        │                🔥 Hotspot                 │
│               │                                          │
│ Weights       │                                          │
│ Population 25%│                                          │
│ Access     25%│                                          │
│ Competition20%│                                          │
│               │                                          │
├───────────────┴──────────────────────────────────────────┤
│ Selected Site: Site A                                    │
│ Overall Score: 84/100                                    │
│ Population 91 | Access 88 | Competition 74 | Risk 79   │
└──────────────────────────────────────────────────────────┘
```

---

# 37. Data Strategy for the Hackathon

Do not spend the majority of the hackathon trying to collect perfect real-world data.

Use a combination of:

```text
Real geospatial data
+
OpenStreetMap data
+
Public geographic datasets
+
Synthetic competitor data
+
Synthetic candidate sites
```

The application architecture should make these sources replaceable.

---

# 38. Recommended MVP Dataset

For the first working version, prepare:

```text
1 metropolitan area

5+ geospatial layers:

1. population.geojson
2. roads.geojson
3. competitors.geojson
4. landuse.geojson
5. risk.geojson
```

Example directory:

```text
data/
├── population.geojson
├── roads.geojson
├── competitors.geojson
├── landuse.geojson
└── risk.geojson
```

---

# 39. Example Synthetic Candidate Sites

```json
[
  {
    "id": "SITE_A",
    "name": "Central Zone",
    "latitude": 22.3039,
    "longitude": 70.8022
  },
  {
    "id": "SITE_B",
    "name": "Highway Zone",
    "latitude": 22.2916,
    "longitude": 70.7933
  },
  {
    "id": "SITE_C",
    "name": "Industrial Zone",
    "latitude": 22.2810,
    "longitude": 70.8230
  }
]
```

These coordinates are only example placeholders for development. Replace them with the geographic area and data your team actually uses.

---

# 40. Project Folder Structure

Recommended repository:

```text
GeoReady-AI/
│
├── README.md
├── PROJECT_PLAN.md
├── .gitignore
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── map/
│   │   ├── charts/
│   │   ├── services/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── geospatial/
│   │   ├── scoring/
│   │   ├── clustering/
│   │   └── ai/
│   ├── requirements.txt
│   └── ...
│
├── data/
│   ├── population.geojson
│   ├── roads.geojson
│   ├── competitors.geojson
│   ├── landuse.geojson
│   └── risk.geojson
│
├── scripts/
│   ├── generate_data.py
│   ├── preprocess.py
│   └── seed_database.py
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── methodology.md
│
└── tests/
    ├── backend/
    └── frontend/
```

---

# 41. Recommended Development Order

Do not build everything simultaneously.

## Phase 1 — Repository Setup

Create:

```text
frontend/
backend/
data/
scripts/
docs/
tests/
```

Then commit:

```bash
git add .
git commit -m "chore: initialize project structure"
git push
```

---

# 42. Phase 2 — Backend

Create FastAPI application.

Minimum:

```text
GET /api/health
GET /api/layers
POST /api/analyze
```

Verify the API works before building complex frontend features.

---

# 43. Phase 3 — Load Geospatial Data

Use GeoPandas.

Example flow:

```python
population = geopandas.read_file(
    "data/population.geojson"
)

competitors = geopandas.read_file(
    "data/competitors.geojson"
)
```

Validate:

```text
CRS
geometry validity
missing values
duplicate records
coordinate ranges
```

---

# 44. Phase 4 — Build Scoring Engine

Create:

```text
backend/app/scoring/
```

Suggested files:

```text
population.py
accessibility.py
competition.py
landuse.py
environment.py
engine.py
```

The engine should return:

```json
{
  "population": 91,
  "accessibility": 88,
  "competition": 74,
  "land_use": 86,
  "environment": 79,
  "overall": 84
}
```

Write tests for this before integrating the UI.

---

# 45. Phase 5 — Interactive Map

Frontend should first display:

```text
Base map
+
candidate sites
+
five layers
```

Then add:

```text
layer toggles
site selection
score panel
```

---

# 46. Phase 6 — Site Analysis

When a user clicks a site:

```text
Frontend
   ↓
POST /api/analyze
   ↓
Backend
   ↓
Calculate all factor scores
   ↓
Return result
   ↓
Frontend displays score
```

---

# 47. Phase 7 — Weight Controls

Add sliders.

Example:

```text
Population       30
Accessibility    20
Competition      20
Land Use         15
Environment      15
```

Validation:

```text
sum(weights) = 100
```

Then recalculate the score instantly.

---

# 48. Phase 8 — Hotspots

Start with a simple implementation:

```text
Generate H3 cells
      ↓
Calculate score for each cell
      ↓
Color cells by readiness
```

Example:

```text
0–20     Low
21–40    Weak
41–60    Medium
61–80    Good
81–100   High
```

These labels are UI categories, not absolute real-world standards.

---

# 49. Phase 9 — Catchment / Accessibility

Add:

```text
10 min
20 min
30 min
```

When a site is selected:

```text
calculate accessible area
+
estimate population inside area
```

Display:

```text
10 min → 12.4K
20 min → 38.7K
30 min → 72.1K
```

---

# 50. Phase 10 — AI Explanation

Use the calculated results as structured input to an LLM.

Example prompt concept:

```text
You are a geospatial business analyst.

Explain why this candidate site received its score.

Do not invent geographic facts.
Use only the supplied metrics.

Site:
EV charging station

Population score: 91
Accessibility score: 88
Competition score: 74
Land-use score: 86
Environmental score: 79
Overall score: 84
```

Expected output:

```text
The site performs strongly because it combines high nearby
population with good transportation accessibility. Competition
is moderate, while environmental conditions introduce some risk.
```

---

# 51. Phase 11 — Site Comparison

Allow the user to select:

```text
2–3 sites
```

Show:

```text
Score cards
Bar charts
Factor comparison
Map markers
Reasons
Risks
```

---

# 52. Phase 12 — Export Report

Create a report containing:

```text
Site details
Map
Overall score
Factor scores
Weights
Nearby features
Catchment results
Reasons
Risks
```

Possible output:

```text
PDF
JSON
CSV
```

For the hackathon, PDF or downloadable JSON is enough.

---

# 53. Important Edge Cases

Handle these cases:

## Missing Data

```text
Population data unavailable
```

Do not silently treat it as zero.

Display:

```text
Data unavailable
```

or use a clearly documented fallback.

## Invalid Geometry

Run geometry validation before analysis.

## No Competitors Nearby

This should be different from missing competitor data.

```text
0 competitors found
```

means actual zero.

```text
Competitor data unavailable
```

means unknown.

## Weight Sum Not 100%

Reject the analysis request.

```text
400 Bad Request
```

with:

```text
Weights must sum to 100%.
```

---

# 54. Performance Considerations

Do not calculate expensive operations repeatedly.

Use:

```text
Spatial indexes
Cached analysis results
Preprocessed H3 cells
PostGIS indexes
```

For example:

```sql
CREATE INDEX competitors_geom_idx
ON competitors
USING GIST (geometry);
```

---

# 55. Security

Minimum requirements:

```text
Validate API input
Limit uploaded file size
Validate uploaded file type
Never expose database credentials
Use environment variables for secrets
Do not commit API keys to GitHub
```

Example:

```text
.env

DATABASE_URL=...
LLM_API_KEY=...
MAP_API_KEY=...
```

Add `.env` to `.gitignore`.

Even though the repository currently has no `.gitignore`, create one locally before adding secrets.

---

# 56. Testing Strategy

## Backend Unit Tests

Test:

```text
population scoring
competition scoring
distance decay
weight calculation
constraint handling
final score calculation
```

Example:

```text
Input scores:
90, 80, 70, 60, 50

Expected final score:
depending on configured weights
```

## API Tests

Test:

```text
GET /health
POST /analyze
POST /compare
POST /hotspots
```

## Frontend Tests

At minimum verify:

```text
Map loads
Layers toggle
Site selection works
Score panel updates
Weight controls work
Comparison works
```

---

# 57. Git Branch Strategy

Use branches so multiple team members can work simultaneously.

```text
main
│
├── feature/map
├── feature/scoring-engine
├── feature/backend-api
├── feature/hotspot-analysis
└── feature/ai-explanation
```

Workflow:

```bash
git checkout -b feature/scoring-engine
```

After work:

```bash
git add .
git commit -m "feat: implement site readiness scoring"
git push -u origin feature/scoring-engine
```

Then create a Pull Request into `main`.

---

# 58. Team Division

For a 4-person team:

## Member 1 — Frontend + Map

```text
React
MapLibre
Dashboard
Layer controls
Site analysis UI
```

## Member 2 — Backend

```text
FastAPI
API endpoints
Database
Data ingestion
```

## Member 3 — Geospatial / ML

```text
GeoPandas
Shapely
H3
DBSCAN
Scoring engine
Catchment analysis
```

## Member 4 — AI + Integration

```text
LLM explanation
Report generation
Frontend/backend integration
Testing
Demo preparation
```

For a 2-person team, combine:

```text
Person 1:
Frontend + integration

Person 2:
Backend + geospatial + AI
```

---

# 59. Minimum Viable Product

If development time becomes limited, finish these first:

```text
1. Interactive map
2. Five geospatial layers
3. Candidate site selection
4. Site Readiness Score
5. Configurable weights
6. Score breakdown
7. Hotspot heatmap
8. Site comparison
9. AI explanation
```

These should be considered the MVP.

---

# 60. Features to Build Only After MVP

Optional advanced features:

```text
10/20/30 minute isochrones
Custom polygon analysis
PDF reports
Advanced clustering
Real-time data updates
Authentication
Multiple metropolitan areas
Cloud deployment
Advanced forecasting
```

Do not delay the core demo while trying to finish all advanced features.

---

# 61. Suggested Demo Scenario

Use one clear scenario.

### Scenario

```text
Business Type:
EV Charging Station

Area:
One metropolitan region

Goal:
Find the most suitable areas for a new charging station.
```

### Demo Flow

```text
1. Open GeoReady-AI
        ↓
2. Display city map
        ↓
3. Turn on Population layer
        ↓
4. Turn on Roads layer
        ↓
5. Turn on Competitor layer
        ↓
6. Turn on Land Use layer
        ↓
7. Turn on Environmental Risk layer
        ↓
8. Display readiness heatmap
        ↓
9. Click Candidate Site A
        ↓
10. Show 84/100
        ↓
11. Show score breakdown
        ↓
12. Show explanation
        ↓
13. Change weights
        ↓
14. Score updates
        ↓
15. Compare Site A and Site B
        ↓
16. Open catchment analysis
        ↓
17. Generate report
```

---

# 62. Example Final Dashboard

```text
============================================================
                     GeoReady-AI
        AI-Powered Geospatial Site Readiness
============================================================

Business Type: EV Charging Station

Overall Candidate Score
             84 / 100

------------------------------------------------------------
Population          91
Accessibility       88
Competition         74
Land Use            86
Environment         79
------------------------------------------------------------

AI Summary

"Strong population density and road accessibility make this
location attractive. Competition is moderate and environmental
risk is the primary factor reducing the score."

------------------------------------------------------------

Catchment

10 minutes     12,400 people
20 minutes     38,700 people
30 minutes     72,100 people

------------------------------------------------------------

Nearby Competitors: 3
Nearest Major Road: 0.8 km
Risk Level: Moderate

[ Compare Site ]     [ Generate Report ]
============================================================
```

---

# 63. Success Criteria

The project should satisfy these technical requirements:

```text
[ ] At least 5 geospatial layers
[ ] Interactive map
[ ] Site selection
[ ] Site score from 0–100
[ ] Configurable weights
[ ] Distance-based analysis
[ ] Competitive density
[ ] Hotspot / clustering visualization
[ ] Layer toggle and opacity
[ ] Custom location/polygon analysis
[ ] Site comparison
[ ] Accessibility / catchment analysis
[ ] AI-generated explanation
[ ] Report export
```

---

# 64. Recommended Final Architecture

```text
                         USER
                           │
                           ▼
                 ┌──────────────────┐
                 │ React + MapLibre │
                 └────────┬─────────┘
                          │
                       REST API
                          │
                          ▼
                 ┌──────────────────┐
                 │     FastAPI      │
                 ├──────────────────┤
                 │ Site Analysis    │
                 │ Scoring Engine   │
                 │ Spatial Analysis │
                 │ Clustering       │
                 │ Catchment        │
                 │ Report API       │
                 └────────┬─────────┘
                          │
              ┌───────────┼────────────┐
              │           │            │
              ▼           ▼            ▼
         ┌────────┐  ┌──────────┐  ┌─────────┐
         │PostGIS │  │GeoPandas │  │   LLM   │
         └────────┘  └──────────┘  └─────────┘
              │
              ▼
      Geographic Data Layers

Population
Roads
Competitors
Land Use
Environmental Risk
```

---

# 65. First Coding Tasks

Start in this exact order:

```text
TASK 1
Create repository structure.

TASK 2
Create React frontend.

TASK 3
Create FastAPI backend.

TASK 4
Add /api/health endpoint.

TASK 5
Prepare five GeoJSON datasets.

TASK 6
Display the five layers on the map.

TASK 7
Create candidate site markers.

TASK 8
Implement individual factor scoring.

TASK 9
Implement weighted final score.

TASK 10
Create site analysis API.

TASK 11
Connect frontend to API.

TASK 12
Add configurable weights.

TASK 13
Add readiness heatmap.

TASK 14
Add hotspot analysis.

TASK 15
Add site comparison.

TASK 16
Add catchment analysis.

TASK 17
Add AI explanation.

TASK 18
Add report export.

TASK 19
Test complete demo.

TASK 20
Deploy.
```

---

# 66. Most Important Engineering Principle

Keep the architecture separated:

```text
DATA
  ↓
GEOSPATIAL PROCESSING
  ↓
SCORING
  ↓
API
  ↓
UI
  ↓
AI EXPLANATION
```

Do **not** put all logic inside React.

The numerical score should be reproducible:

```text
Same input
+
Same weights
=
Same score
```

The AI should explain the result, not secretly change the result.

---

# 67. Final Project Definition

### One-line description

> GeoReady-AI is an AI-powered geospatial decision-support platform that analyzes multiple geographic factors to identify, score, compare, and explain the readiness of potential sites for new facilities.

### Core question answered by the platform

> **"Where should we consider placing a new facility, and what geographic factors explain the site's readiness score?"**

### Core technical components

```text
Geospatial Data
+
Spatial Analysis
+
Weighted Scoring
+
Hotspot Detection
+
Accessibility Analysis
+
Interactive Maps
+
Explainable AI
```

### MVP priority

```text
MAP
   ↓
5 LAYERS
   ↓
SITE ANALYSIS
   ↓
0–100 SCORE
   ↓
WEIGHT CONTROLS
   ↓
HEATMAP
   ↓
SITE COMPARISON
   ↓
AI EXPLANATION
```

This is the implementation path the team should follow.