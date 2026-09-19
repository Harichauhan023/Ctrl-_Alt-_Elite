# 🏆 GeoReady-AI — Pitch Outline (3 minutes)

## The problem (20 s)
Every year, businesses burn money placing facilities by instinct. An EV network, a warehouse,
a retail chain — each decision needs population, roads, competitors, zoning and environmental-risk
data… from **five different sources** that never speak to each other. Wrong siting costs lakhs
per location and months to discover.

## The product (30 s)
**GeoReady-AI** is a geospatial decision-support platform that turns six siloed datasets into
**one reproducible number**: a 0–100 Site Readiness Score — with the map, the breakdown,
and a plain-language explanation of *why*.
- 🔥 City-wide H3 readiness heatmap — "where should we even look"
- ⚖️ Configurable factor weights — mirrors each committee's judgement
- ⛔ Hard constraints (protected land, critical flood zones) that override any score
- 🤖 Knowledge-grounded AI explanation that *can never invent a number*

## Why judges should care (60 s) — the differentiators
1. **Deterministic core, AI on the edges.** The engine computes; the LLM only narrates.
   Same input + same weights ⇒ same score — auditable, testable (we ship pytest).
2. **Built for failure.** 4-provider Gemini failover with cooldown; when every provider dies,
   a deterministic explainer answers in the identical JSON shape. Venue Wi-Fi down?
   The basemap flips to offline-safe and *the entire demo keeps running*.
3. **Real geography.** Built on our own Rajkot: 1,538 real OpenStreetMap roads, real hospitals,
   schools, fuel stations — fused with clearly-labelled synthetic layers that swap for municipal
   data with zero code changes.
4. **Honest about approximations.** Catchment rings are labelled travel-shed approximations with a
   documented OSRM upgrade path. Trust is a feature.

## Market framing (20 s)
Same engine, different weight presets: retail (population-led), warehouse (zoning+highway led),
telecom (coverage led), renewables (environment led) — six business types shipped today.
Any city = one data-pipeline run. Municipal planning boards, charge-point operators, logistics
networks, ONDC-era retail — all buy "where do we put the next one?" answers.

## The ask (10 s)
Deploy GeoReady-AI as the screening layer before expensive feasibility studies:
kill the bad sites in minutes, spend human expertise on the five that matter.

> **Tagline:** *"GeoReady-AI doesn't just answer where — it shows why."*
