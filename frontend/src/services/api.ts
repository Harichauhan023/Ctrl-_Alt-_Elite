import type {
  AnalysisResult, BusinessType, CatchmentResponse, ChatMsg, ExplainResponse, MlInsights,
  FactorScores, LayerInfo, PolygonResponse, RecommendResponse, Site, WeightsPct,
} from "../types";

const BASE = "/api";

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let msg = `${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail || JSON.stringify(body);
    } catch { /* keep status */ }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

const post = <T,>(path: string, body: unknown) =>
  j<T>(path, { method: "POST", body: JSON.stringify(body) });

export const pctToWire = (w: WeightsPct) => ({
  population: w.population, accessibility: w.accessibility, competition: w.competition,
  land_use: w.land_use, environment: w.environment,
});

export const api = {
  health: () => j<any>("/health"),
  stats: () => j<any>("/stats"),
  layers: () => j<{ layers: LayerInfo[]; study_area: string; center: any; bbox: any }>("/layers"),
  layerData: (name: string) => j<GeoJSON.FeatureCollection>(`/layers/${name}/data`),
  businessTypes: () => j<{ business_types: BusinessType[] }>("/business-types"),
  sites: () => j<{ sites: Site[] }>("/sites"),
  createSite: (body: { name: string; latitude: number; longitude: number; business_type: string }) =>
    post<Site>("/sites", body),
  deleteSite: (id: string) => j<any>(`/sites/${id}`, { method: "DELETE" }),
  analyze: (body: {
    name?: string | null; latitude: number; longitude: number;
    business_type: string; weights?: WeightsPct;
    extra_competitors?: { latitude: number; longitude: number }[];
  }) => post<AnalysisResult>("/analyze", body),
  analyzeAll: (body: {
    latitude: number; longitude: number;
    extra_competitors?: { latitude: number; longitude: number }[];
  }) => post<{ results: Record<string, AnalysisResult> }>("/analyze_all", body),
  recommend: (body: {
    business_type: string; weights?: WeightsPct; top_k?: number;
    min_population?: number; max_competitors_1km?: number; exclude_constrained?: boolean;
    polygon?: number[][];
  }) => post<RecommendResponse>("/recommend", body),
  polygonAnalyze: (body: { polygon: number[][]; business_type: string; weights?: WeightsPct }) =>
    post<PolygonResponse>("/polygon", body),
  chat: (message: string, context?: Record<string, unknown>) =>
    post<{ reply: string; action: string; data: any; citations: string[]; used_llm: boolean; provider: string | null }>(
      "/chat", { message, context: context ?? null }),
  ragSearch: (q: string, k = 6) =>
    j<{ mode: string; total_docs: number; chunks: { title: string; text: string; tags: string[]; score: number }[] }>(
      `/rag/search?q=${encodeURIComponent(q)}&k=${k}`),
  mlInsights: () => j<MlInsights>("/ml/insights"),
  compare: (body: {
    points: { name?: string | null; latitude: number; longitude: number }[];
    business_type: string; weights?: WeightsPct;
  }) => post<{ results: AnalysisResult[]; winners: Record<string, string>; narrative: string[] }>(
    "/compare", body),
  catchment: (latitude: number, longitude: number) =>
    post<CatchmentResponse>("/catchment", { latitude, longitude }),
  explain: (analysis: AnalysisResult, question?: string) =>
    post<ExplainResponse>("/explain", { analysis, question: question || null }),
  report: (analysis: AnalysisResult, catchment?: unknown, explanation?: unknown) =>
    post<any>("/report", { analysis, catchment: catchment || null, explanation: explanation || null }),
  hotspots: (business: string, weights?: FactorScores | null) => {
    const q = new URLSearchParams({ business_type: business });
    if (weights) {
      q.set("wp", String(Math.round(weights.population * 100)));
      q.set("wa", String(Math.round(weights.accessibility * 100)));
      q.set("wc", String(Math.round(weights.competition * 100)));
      q.set("wl", String(Math.round(weights.land_use * 100)));
      q.set("we", String(Math.round(weights.environment * 100)));
    }
    return j<{ geojson: GeoJSON.FeatureCollection; cells: number }>(`/hotspots?${q}`);
  },
};
