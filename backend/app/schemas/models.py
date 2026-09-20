from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

FACTOR_KEYS = ["population", "accessibility", "competition", "land_use", "environment"]


class LatLng(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Weights(BaseModel):
    population: float = Field(ge=0, le=100)
    accessibility: float = Field(ge=0, le=100)
    competition: float = Field(ge=0, le=100)
    land_use: float = Field(ge=0, le=100)
    environment: float = Field(ge=0, le=100)

    @field_validator("*", mode="before")
    @classmethod
    def _pct(cls, v):
        return float(v)

    def as_fraction(self) -> dict:
        raw = {k: getattr(self, k) for k in FACTOR_KEYS}
        total = sum(raw.values())
        if abs(total - 100) > 5:
            raise ValueError(f"Weights must sum to 100% (got {total:.1f}%).")
        return {k: v / total for k, v in raw.items()} if total else raw


class AnalyzeRequest(BaseModel):
    name: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    business_type: str = "EV_CHARGING"
    weights: Weights | None = None  # percentages summing to 100
    extra_competitors: list[LatLng] | None = None  # what-if scenario ghost competitors


class RecommendRequest(BaseModel):
    business_type: str = "EV_CHARGING"
    weights: Weights | None = None
    top_k: int = Field(default=5, ge=1, le=12)
    min_population: float = Field(default=0, ge=0, le=100)      # min population SCORE
    max_competitors_1km: int = Field(default=99, ge=0)          # max rivals within 1 km
    exclude_constrained: bool = True                            # skip hard-constraint cells
    polygon: list[list[float]] | None = None                    # optional [[lng,lat],...] area filter


class PolygonAnalyzeRequest(BaseModel):
    polygon: list[list[float]] = Field(min_length=3)            # [[lng,lat],...]
    business_type: str = "EV_CHARGING"
    weights: Weights | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: dict | None = None  # {last_analysis?, business_type?} from the UI


class ChatResponse(BaseModel):
    reply: str
    action: str
    data: dict | None = None
    citations: list[str]
    used_llm: bool
    provider: str | None = None


class ComparePoint(BaseModel):
    name: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CompareRequest(BaseModel):
    points: list[ComparePoint] = Field(min_length=2, max_length=4)
    business_type: str = "EV_CHARGING"
    weights: Weights | None = None


class CatchmentRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ExplainRequest(BaseModel):
    analysis: dict
    question: str | None = None


class ReportRequest(BaseModel):
    analysis: dict
    catchment: dict | None = None
    explanation: dict | None = None


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    business_type: str = "EV_CHARGING"
