"""ML transparency endpoints — real artifacts, real metrics (spec §11/§12)."""
from __future__ import annotations

from fastapi import APIRouter

from ..services.ml_service import get_ml_service

router = APIRouter()


@router.get("/ml/insights")
def ml_insights():
    """Model card: algorithm, training size, REAL holdout metrics and feature
    importance read from the persisted artifacts — nothing invented."""
    svc = get_ml_service()
    meta = svc.meta()
    return {
        **meta,
        "store": "ml/models/ (site_readiness_model.joblib + metrics.json + feature_importance.json)",
        "note": "Predictions use the 13-feature schema only — UI weight sliders never touch them.",
    }
