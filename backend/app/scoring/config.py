"""
Business-type scoring configurations.

`weights` are the default factor weights (user can override via UI sliders).
`landuse` maps land-use category → suitability 0-100 for that business.
`competition_polarity`:
    "avoid"   → fewer/ farther competitors = better (most businesses)
    "attract" → competitor presence validates the market (e.g. some retail)

All values are editable methodology assumptions, not universal business rules
(PS-2 §25/§31/§56).
"""

BUSINESS_CONFIGS: dict[str, dict] = {
    "EV_CHARGING": {
        "label": "EV Charging Station",
        "description": "Public charging points — demand, road access & grid-friendly siting.",
        "weights": {"population": 0.20, "accessibility": 0.35, "competition": 0.20,
                    "land_use": 0.10, "environment": 0.15},
        "landuse": {"commercial": 95, "mixed_use": 85, "industrial": 75, "residential": 55,
                    "agricultural": 20, "protected": 0, "unknown": 50},
        "competition_polarity": "avoid",
    },
    "RETAIL": {
        "label": "Retail Store",
        "description": "Customer-facing retail — footfall & catchment population driven.",
        "weights": {"population": 0.30, "accessibility": 0.25, "competition": 0.20,
                    "land_use": 0.15, "environment": 0.10},
        "landuse": {"commercial": 100, "mixed_use": 90, "industrial": 50, "residential": 70,
                    "agricultural": 15, "protected": 0, "unknown": 50},
        "competition_polarity": "attract",
    },
    "WAREHOUSE": {
        "label": "Warehouse / Fulfilment",
        "description": "Logistics & storage — highway access and suitable zoning dominate.",
        "weights": {"population": 0.05, "accessibility": 0.35, "competition": 0.05,
                    "land_use": 0.40, "environment": 0.15},
        "landuse": {"commercial": 70, "mixed_use": 60, "industrial": 100, "residential": 15,
                    "agricultural": 40, "protected": 0, "unknown": 50},
        "competition_polarity": "avoid",
    },
    "TELECOM_TOWER": {
        "label": "Telecom Tower",
        "description": "Network coverage asset — proximity to users, tolerant zoning.",
        "weights": {"population": 0.25, "accessibility": 0.25, "competition": 0.10,
                    "land_use": 0.20, "environment": 0.20},
        "landuse": {"commercial": 60, "mixed_use": 75, "industrial": 80, "residential": 75,
                    "agricultural": 85, "protected": 0, "unknown": 50},
        "competition_polarity": "avoid",
    },
    "SERVICE_CENTER": {
        "label": "Service Center",
        "description": "Customer service hub — population reach with easy access.",
        "weights": {"population": 0.30, "accessibility": 0.30, "competition": 0.15,
                    "land_use": 0.15, "environment": 0.10},
        "landuse": {"commercial": 100, "mixed_use": 90, "industrial": 65, "residential": 60,
                    "agricultural": 15, "protected": 0, "unknown": 50},
        "competition_polarity": "avoid",
    },
    "RENEWABLE": {
        "label": "Renewable Energy Facility",
        "description": "Solar/small-wind — open land, low environmental conflict.",
        "weights": {"population": 0.05, "accessibility": 0.20, "competition": 0.05,
                    "land_use": 0.30, "environment": 0.40},
        "landuse": {"commercial": 30, "mixed_use": 40, "industrial": 80, "residential": 20,
                    "agricultural": 90, "protected": 0, "unknown": 50},
        "competition_polarity": "avoid",
    },
}

ENV_SCORE_MAP = {"low": 100, "medium": 60, "high": 20, "critical": 0}
ENV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

STATUS_BANDS = [
    (80, "HIGH_POTENTIAL"),
    (65, "GOOD"),
    (50, "MODERATE"),
    (35, "WEAK"),
    (0, "LOW"),
]

HEATMAP_BANDS = [
    (80, "High",   "#22c55e"),
    (60, "Good",   "#84cc16"),
    (40, "Medium", "#f59e0b"),
    (20, "Weak",   "#f97316"),
    (0,  "Low",    "#ef4444"),
]


def get_business(key: str) -> dict:
    cfg = BUSINESS_CONFIGS.get((key or "").upper().replace(" ", "_"))
    if not cfg:
        raise KeyError(key)
    return cfg


def status_for(score: float) -> str:
    for cut, label in STATUS_BANDS:
        if score >= cut:
            return label
    return "LOW"


def heatband_for(score: float) -> tuple[str, str]:
    for cut, label, color in HEATMAP_BANDS:
        if score >= cut:
            return label, color
    return "Low", "#ef4444"
