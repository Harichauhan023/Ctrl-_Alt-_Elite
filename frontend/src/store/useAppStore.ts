import { create } from "zustand";
import type {
  AnalysisResult, BusinessType, CatchmentResponse, ExplainResponse,
  PolygonResponse, RecommendZone, Site, WeightsPct,
} from "../types";

export const FACTOR_KEYS = ["population", "accessibility", "competition", "land_use", "environment"] as const;
export type FactorKey = (typeof FACTOR_KEYS)[number];

export const FACTOR_META: Record<FactorKey, { label: string; short: string; color: string }> = {
  population:    { label: "Population",     short: "POP", color: "#38bdf8" },
  accessibility: { label: "Accessibility",  short: "ACC", color: "#34d399" },
  competition:   { label: "Competition",    short: "CMP", color: "#fbbf24" },
  land_use:      { label: "Land Use",       short: "LND", color: "#a78bfa" },
  environment:   { label: "Environment",    short: "ENV", color: "#fb7185" },
};

export const DEFAULT_LAYER_STATE: Record<string, { visible: boolean; opacity: number }> = {
  population:  { visible: true,  opacity: 0.55 },
  roads:       { visible: true,  opacity: 0.9 },
  competitors: { visible: true,  opacity: 1.0 },
  landuse:     { visible: false, opacity: 0.45 },
  risk:        { visible: false, opacity: 0.5 },
  hospitals:   { visible: false, opacity: 1.0 },
  schools:     { visible: false, opacity: 1.0 },
  fuel:        { visible: false, opacity: 1.0 },
};

export const LAYER_COLORS: Record<string, string> = {
  population: "#0ea5e9", roads: "#e2e8f0", competitors: "#ef4444",
  landuse: "#a78bfa", risk: "#f97316", hospitals: "#2dd4bf",
  schools: "#c084fc", fuel: "#94a3b8",
};

interface AppState {
  businessType: string;
  businessTypes: BusinessType[];
  weights: WeightsPct;
  rightTab: "analysis" | "area" | "assistant";
  rightDockOpen: boolean;
  basemap: "dark" | "streets" | "satellite";
  drawMode: false | "polygon" | "ghost";
  polygonCoords: number[][] | null;
  polygonResult: PolygonResponse | null;
  recommendZones: RecommendZone[];
  ghostCompetitors: { lat: number; lng: number }[];
  layerState: Record<string, { visible: boolean; opacity: number }>;
  heatmapOn: boolean;
  sites: Site[];
  pin: { lat: number; lng: number; name?: string } | null;
  analysis: AnalysisResult | null;
  analyzing: boolean;
  analysisError: string | null;
  catchment: CatchmentResponse | null;
  catchmentOn: boolean;
  explanation: ExplainResponse | null;
  explaining: boolean;
  compareList: AnalysisResult[];
  sidebarOpen: boolean;

  setBusinessType: (b: string) => void;
  setBusinessTypes: (b: BusinessType[]) => void;
  setWeight: (k: FactorKey, v: number) => void;
  normalizeWeights: () => void;
  resetWeights: () => void;
  toggleLayer: (name: string) => void;
  setLayerOpacity: (name: string, v: number) => void;
  setHeatmapOn: (v: boolean) => void;
  setSites: (s: Site[]) => void;
  setPin: (p: AppState["pin"]) => void;
  setAnalysis: (a: AnalysisResult | null) => void;
  setAnalyzing: (v: boolean) => void;
  setAnalysisError: (e: string | null) => void;
  setCatchment: (c: CatchmentResponse | null) => void;
  setCatchmentOn: (v: boolean) => void;
  setExplanation: (e: ExplainResponse | null) => void;
  setExplaining: (v: boolean) => void;
  addToCompare: (a: AnalysisResult) => void;
  removeFromCompare: (name: string) => void;
  clearCompare: () => void;
  setSidebarOpen: (v: boolean) => void;
  setRightTab: (t: AppState["rightTab"]) => void;
  setRightDockOpen: (v: boolean) => void;
  setBasemap: (v: AppState["basemap"]) => void;
  setDrawMode: (v: false | "polygon" | "ghost") => void;
  setPolygon: (coords: number[][] | null, result: PolygonResponse | null) => void;
  setRecommendZones: (z: RecommendZone[]) => void;
  addGhost: (g: { lat: number; lng: number }) => void;
  removeGhost: (i: number) => void;
  clearGhosts: () => void;
}

const EV_DEFAULT: WeightsPct = {
  population: 20, accessibility: 35, competition: 20, land_use: 10, environment: 15,
};

export const useAppStore = create<AppState>((set, get) => ({
  businessType: "EV_CHARGING",
  businessTypes: [],
  weights: EV_DEFAULT,
  rightTab: "analysis",
  rightDockOpen: true,
  basemap: (typeof window !== "undefined" && (localStorage.getItem("geoready_basemap") as AppState["basemap"])) || "streets",
  drawMode: false,
  polygonCoords: null,
  polygonResult: null,
  recommendZones: [],
  ghostCompetitors: [],
  layerState: DEFAULT_LAYER_STATE,
  heatmapOn: false,
  sites: [],
  pin: null,
  analysis: null,
  analyzing: false,
  analysisError: null,
  catchment: null,
  catchmentOn: false,
  explanation: null,
  explaining: false,
  compareList: [],
  sidebarOpen: true,

  setBusinessType: (businessType) => {
    const bt = get().businessTypes.find((b) => b.key === businessType);
    const defaults = bt
      ? Object.fromEntries(Object.entries(bt.default_weights).map(([k, v]) => [k, Math.round(v * 100)]))
      : EV_DEFAULT;
    set({ businessType, weights: defaults as unknown as WeightsPct, heatmapOn: false });
  },
  setBusinessTypes: (businessTypes) => set({ businessTypes }),
  setWeight: (k, v) => set((s) => ({ weights: { ...s.weights, [k]: v } })),
  normalizeWeights: () => set((s) => {
    const entries = FACTOR_KEYS.map((k) => [k, s.weights[k]] as const);
    const total = entries.reduce((a, [, v]) => a + v, 0) || 1;
    const weights = Object.fromEntries(entries.map(([k, v]) => [k, Math.round((v / total) * 100)]));
    // drift fix on the largest bucket
    const sum = Object.values(weights).reduce((a: number, b) => a + (b as number), 0);
    const big = FACTOR_KEYS.reduce((a, b) => (weights[a]! > weights[b]! ? a : b));
    weights[big] = (weights[big] as number) + (100 - sum);
    return { weights: weights as unknown as WeightsPct };
  }),
  resetWeights: () => {
    const bt = get().businessTypes.find((b) => b.key === get().businessType);
    if (bt) {
      set({
        weights: Object.fromEntries(
          Object.entries(bt.default_weights).map(([k, v]) => [k, Math.round(v * 100)]),
        ) as unknown as WeightsPct,
      });
    } else set({ weights: EV_DEFAULT });
  },
  toggleLayer: (name) => set((s) => ({
    layerState: { ...s.layerState, [name]: { ...s.layerState[name], visible: !s.layerState[name]?.visible } },
  })),
  setLayerOpacity: (name, v) => set((s) => ({
    layerState: { ...s.layerState, [name]: { ...s.layerState[name], opacity: v } },
  })),
  setHeatmapOn: (v) => set({ heatmapOn: v }),
  setSites: (sites) => set({ sites }),
  setPin: (pin) => set({ pin, explanation: null }),
  setAnalysis: (analysis) => set({ analysis }),
  setAnalyzing: (analyzing) => set({ analyzing }),
  setAnalysisError: (analysisError) => set({ analysisError }),
  setCatchment: (catchment) => set({ catchment }),
  setCatchmentOn: (catchmentOn) => set({ catchmentOn }),
  setExplanation: (explanation) => set({ explanation }),
  setExplaining: (explaining) => set({ explaining }),
  addToCompare: (a) => set((s) => {
    const name = a.name || `Pin ${a.latitude.toFixed(4)},${a.longitude.toFixed(4)}`;
    if (s.compareList.some((c) => (c.name || "") === name) || s.compareList.length >= 4) return {};
    return { compareList: [...s.compareList, { ...a, name }] };
  }),
  removeFromCompare: (name) => set((s) => ({ compareList: s.compareList.filter((c) => c.name !== name) })),
  clearCompare: () => set({ compareList: [] }),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setRightTab: (rightTab) => set({ rightTab, rightDockOpen: true }),
  setRightDockOpen: (rightDockOpen) => set({ rightDockOpen }),
  setBasemap: (basemap) => {
    try { localStorage.setItem("geoready_basemap", basemap); } catch { /* ignore */ }
    set({ basemap });
  },
  setDrawMode: (drawMode) => set({ drawMode }),
  setPolygon: (polygonCoords, polygonResult) => set({ polygonCoords, polygonResult }),
  setRecommendZones: (recommendZones) => set({ recommendZones }),
  addGhost: (g) => set((s) => ({ ghostCompetitors: [...s.ghostCompetitors, g].slice(-10) })),
  removeGhost: (i) => set((s) => ({ ghostCompetitors: s.ghostCompetitors.filter((_, j) => j !== i) })),
  clearGhosts: () => set({ ghostCompetitors: [] }),
}));

export const weightSum = (w: WeightsPct) =>
  FACTOR_KEYS.reduce((a, k) => a + w[k], 0);
