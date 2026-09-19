import { useCallback } from "react";
import { api } from "./api";
import { useAppStore } from "../store/useAppStore";

/** Shared analysis runner — map clicks, site lists and weight changes all funnel here. */
export function useAnalysis() {
  const run = useCallback(async (lat: number, lng: number, name?: string) => {
    const s = useAppStore.getState();
    s.setAnalyzing(true);
    s.setAnalysisError(null);
    s.setExplanation(null);
    try {
      const analysis = await api.analyze({
        name: name ?? s.pin?.name ?? null,
        latitude: lat,
        longitude: lng,
        business_type: s.businessType,
        weights: s.weights,
        extra_competitors: s.ghostCompetitors.length
          ? s.ghostCompetitors.map((g) => ({ latitude: g.lat, longitude: g.lng }))
          : undefined,
      });
      s.setAnalysis(analysis);
      if (useAppStore.getState().catchmentOn) {
        const c = await api.catchment(lat, lng);
        s.setCatchment(c);
      } else {
        s.setCatchment(null);
      }
    } catch (e: any) {
      s.setAnalysis(null);
      s.setAnalysisError(e?.message || "Analysis failed");
    } finally {
      s.setAnalyzing(false);
    }
  }, []);

  const refreshCatchment = useCallback(async () => {
    const s = useAppStore.getState();
    if (!s.analysis) return;
    const c = await api.catchment(s.analysis.latitude, s.analysis.longitude);
    s.setCatchment(c);
  }, []);

  return { run, refreshCatchment };
}
