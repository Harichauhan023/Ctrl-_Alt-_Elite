"""Report export endpoint (PS-2 §52) — downloadable JSON report."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..schemas.models import ReportRequest

router = APIRouter()


@router.post("/report")
def report(req: ReportRequest):
    a = req.analysis
    return {
        "report_type": "GEOREADY_SITE_ANALYSIS",
        "report_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "site": {
            "name": a.get("name") or "Candidate pin",
            "latitude": a.get("latitude"), "longitude": a.get("longitude"),
            "business_type": a.get("business_type"),
        },
        "result": {
            "overall_score": a.get("overall_score"),
            "status": a.get("status"),
            "factor_scores": a.get("scores"),
            "weights_used": a.get("weights"),
            "reasons": a.get("reasons"),
            "risks": a.get("risks"),
            "constraints": a.get("constraints"),
            "details": a.get("details"),
        },
        "catchment": req.catchment,
        "explanation": req.explanation,
        "methodology": {
            "scoring": "weighted sum of five 0-100 normalised factors (population, accessibility, "
                       "competition, land use, environmental risk); configurable weights; "
                       "exponential distance decay; hard constraints override the numeric score.",
            "data": "Real OpenStreetMap roads/POIs + clearly-labelled synthetic layers "
                    "(population model, land use, risk) for the Rajkot study area.",
            "determinism": "Same data + same weights ⇒ same score. AI explains, never computes.",
        },
    }
