export interface FactorScores {
  population: number;
  accessibility: number;
  competition: number;
  land_use: number;
  environment: number;
}

export type WeightsPct = FactorScores; // UI keeps percentages (sum = 100)

export interface AnalysisResult {
  name: string | null;
  latitude: number;
  longitude: number;
  business_type: string;
  business_label: string;
  overall_score: number;
  status: string;
  scores: FactorScores;
  weights: FactorScores;
  details: Record<string, any>;
  constraints: string[];
  reasons: string[];
  risks: string[];
  ml_prediction: number | null;
  ml_available: boolean;
  feature_mode: string;
  ml_features: Record<string, number> | null;
}

export interface Site {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  preset: boolean;
}

export interface Explanation {
  summary: string;
  strengths: string[];
  risks: string[];
  key_reason: string;
  answer?: string;
  sources?: string[];
}

export interface ExplainMeta {
  used_llm: boolean;
  provider: string | null;
  model?: string;
  fallback_reason: string | null;
  rag_mode: string;
  rag_sources: string[];
  sources?: { title: string; source: string; score: number }[];
  pipeline?: { features: string; ml: boolean; rag_chunks: number };
  cached: boolean;
}

export interface MlInsights {
  available: boolean;
  algorithm?: string;
  metrics?: Record<string, any>;
  feature_importance?: { name: string; importance: number }[];
  n_samples?: number;
  generated_at?: string;
}

export interface ExplainResponse {
  explanation: Explanation;
  meta: ExplainMeta;
}

export interface BusinessType {
  key: string;
  label: string;
  description: string;
  default_weights: FactorScores;
  competition_polarity: string;
}

export interface LayerInfo {
  name: string;
  label: string;
  kind: string;
  source: string;
  count: number;
}

export interface CatchmentBand {
  minutes: number;
  radius_km: number;
  reachable_population: number;
  competitors_in_range: number;
}

export interface CatchmentResponse {
  catchments: CatchmentBand[];
  rings_geojson: GeoJSON.FeatureCollection;
  method: string;
}

export interface RecommendZone {
  h3: string;
  latitude: number;
  longitude: number;
  overall: number;
  band: string;
  color: string;
  scores: FactorScores;
  competitors_within_1km: number;
  land_category: string;
  risk_level: string;
}

export interface RecommendResponse {
  business_label: string;
  constraints_applied: Record<string, any>;
  candidates_evaluated: number;
  surviving: number;
  zones: RecommendZone[];
}

export interface PolygonResponse {
  business_label: string;
  area_km2: number;
  population: number;
  population_per_km2: number;
  road_km: number;
  road_density_km_per_km2: number;
  competitors: number;
  zones: {
    count: number; readiness_mean: number; readiness_min: number; readiness_max: number;
    bands: Record<string, number>; constrained_share_pct: number;
  };
  land_use_mix: Record<string, number>;
  risk_mix: Record<string, number>;
  top_cells: { h3: string; latitude: number; longitude: number; overall: number; color: string }[];
  verdict: string[];
  method: string;
}

export interface ChatMsg {
  role: "user" | "assistant";
  text: string;
  action?: string;
  data?: any;
  citations?: string[];
  used_llm?: boolean;
  provider?: string | null;
}
