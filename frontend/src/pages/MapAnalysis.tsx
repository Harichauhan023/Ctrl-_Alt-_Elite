import { useEffect } from "react";
import RightDock from "../components/Analysis/RightDock";
import CompareTray from "../components/CompareTray";
import MapView from "../components/Map/MapView";
import LeftSidebar from "../components/Sidebar/LeftSidebar";
import { api } from "../services/api";
import { useAppStore, weightSum } from "../store/useAppStore";

export default function MapAnalysis() {
  const setSites = useAppStore((s) => s.setSites);
  const setBusinessTypes = useAppStore((s) => s.setBusinessTypes);
  const weights = useAppStore((s) => s.weights);
  const businessType = useAppStore((s) => s.businessType);
  const pin = useAppStore((s) => s.pin);
  const analysis = useAppStore((s) => s.analysis);
  const ghosts = useAppStore((s) => s.ghostCompetitors);

  // initial data
  useEffect(() => {
    api.businessTypes().then((d) => setBusinessTypes(d.business_types)).catch(() => {});
    api.sites().then((d) => setSites(d.sites)).catch(() => {});
  }, [setSites, setBusinessTypes]);

  // live re-analysis on weight/business change (same pin, fresh math)
  useEffect(() => {
    if (!pin || !analysis) return;
    if (Math.abs(weightSum(weights) - 100) > 5) return; // backend would reject
    const t = setTimeout(() => {
      api.analyze({
        name: pin.name ?? analysis.name, latitude: pin.lat, longitude: pin.lng,
        business_type: businessType, weights,
        extra_competitors: ghosts.map((g) => ({ latitude: g.lat, longitude: g.lng })),
      }).then((a) => useAppStore.getState().setAnalysis(a)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weights, businessType]);

  // live re-analysis when simulated rivals change (what-if scenario)
  useEffect(() => {
    if (!pin || !analysis) return;
    const t = setTimeout(() => {
      const st = useAppStore.getState();
      api.analyze({
        name: pin.name ?? analysis.name, latitude: pin.lat, longitude: pin.lng,
        business_type: st.businessType, weights: st.weights,
        extra_competitors: st.ghostCompetitors.map((g) => ({ latitude: g.lat, longitude: g.lng })),
      }).then((a) => st.setAnalysis(a)).catch(() => {});
    }, 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ghosts]);

  return (
    <div className="relative h-full w-full overflow-hidden bg-ink-950">
      <MapView />
      <LeftSidebar />
      <RightDock />
      <CompareTray />
    </div>
  );
}
