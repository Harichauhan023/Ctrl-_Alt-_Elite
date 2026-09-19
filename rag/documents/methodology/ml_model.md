---
title: ML Model — Training, Evaluation & Honesty Notes
tags: [ml, methodology, model]
source: rag/documents/methodology/ml_model.md
---
# ML Model — Training, Evaluation & Honesty Notes

## What the model is
A RandomForestRegressor (scikit-learn, 220 trees, max depth 12) predicting a
0–100 site-readiness score from 13 geospatial features. It is distinct from the
deterministic scoring engine: the deterministic layer applies configurable
business weights and hard constraints; the ML model learned its weights from
10,000 synthetic candidate sites. The UI always shows BOTH numbers side by
side, and the weight sliders never touch the ML prediction.

## Features (13)
population_1km, population_3km, population_density (people/km²),
nearest_major_road_km, road_density (km/km² in a 600 m disc),
competitors_1km, competitors_3km, nearest_competitor_km,
landuse_score (neutral suitability = mean of per-business tables),
environment_risk_score (100/60/20/0), and catchment populations at 10/20/30
minutes. All features come from the same SQL extraction pipeline used by
/api/analyze — there is no separate ML data path.

## Training data and labels
10,000 candidates sampled across the study bbox (75% uniform, 25% clustered at
the urban core; seed 7), features extracted in batch SQL, labels from a
DOCUMENTED baseline rubric in ml/labels.py: 0.25·population + 0.25·access +
0.20·competition(avoid) + 0.15·landuse + 0.15·environment, plus N(0, 2.2)
noise, clipped 1–99, ×0.15 under hard constraints. The labels are a rubric,
not ground truth — the point is demonstrating a real, evaluated ML pipeline.

## Evaluation (real, persisted in ml/models/metrics.json)
20% holdout, seed 42: MAE ≈ 1.85, RMSE ≈ 2.33, R² ≈ 0.96. Feature importance
(persisted in ml/models/feature_importance.json) is dominated by
landuse_score, then nearest_major_road_km — the model learned that zoning and
road access carry the rubric. Run python ml/train.py to reproduce; run
python ml/evaluate.py to re-verify the saved artifact.

## How it is served
The artifact (joblib) loads once at first analysis; /api/analyze returns
ml_prediction alongside the deterministic score and /api/ml/insights returns
the model card. If artifacts are missing the app degrades: ML fields become
null and everything else keeps working.
