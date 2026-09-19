import { useState } from "react";
import { Loader2, Target, Trophy, X } from "lucide-react";
import { flyToSite } from "../../map/singleton";
import { api } from "../../services/api";
import { useAppStore, weightSum } from "../../store/useAppStore";
import type { RecommendZone } from "../../types";

export default function RecommendPanel() {
  const zones = useAppStore((s) => s.recommendZones);
  const setZones = useAppStore((s) => s.setRecommendZones);
  const [minPop, setMinPop] = useState(0);
  const [maxRivals, setMaxRivals] = useState(99);
  const [topK, setTopK] = useState(5);
  const [busy, setBusy] = useState(false);
  const [surviving, setSurviving] = useState<number | null>(null);

  const run = async () => {
    const s = useAppStore.getState();
    if (Math.abs(weightSum(s.weights) - 100) > 5) { alert("Weights must sum to ~100% first."); return; }
    setBusy(true);
    try {
      const r = await api.recommend({
        business_type: s.businessType, weights: s.weights, top_k: topK,
        min_population: minPop, max_competitors_1km: maxRivals, exclude_constrained: true,
      });
      setZones(r.zones);
      setSurviving(r.surviving);
    } catch (e: any) { alert(e.message); } finally { setBusy(false); }
  };

  const analyzeZone = (z: RecommendZone) => {
    const s = useAppStore.getState();
    const name = `Zone ${z.h3.slice(-6)}`;
    s.setPin({ lat: z.latitude, lng: z.longitude, name });
    s.setRightTab("analysis");
    flyToSite(z.latitude, z.longitude, 14);
    s.setAnalyzing(true); s.setAnalysisError(null);
    api.analyze({ name, latitude: z.latitude, longitude: z.longitude,
                  business_type: s.businessType, weights: s.weights })
      .then((a) => s.setAnalysis(a)).catch((e) => s.setAnalysisError(e.message))
      .finally(() => s.setAnalyzing(false));
  };

  return (
    <div className="glass rounded-xl p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="panel-title flex items-center gap-1"><Trophy size={11} className="text-amber-400" /> Site recommender</div>
        {zones.length > 0 && (
          <button onClick={() => { setZones([]); setSurviving(null); }}
            className="text-slate-500 hover:text-danger-400"><X size={12} /></button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-1.5 text-[10px]">
        <label className="rounded-lg bg-ink-800 px-1.5 py-1">
          <span className="text-slate-500">min pop</span>
          <input type="number" min={0} max={100} value={minPop}
            onChange={(e) => setMinPop(Math.max(0, Math.min(100, Number(e.target.value))))}
            className="w-full bg-transparent font-mono text-slate-100 outline-none" />
        </label>
        <label className="rounded-lg bg-ink-800 px-1.5 py-1">
          <span className="text-slate-500">max rivals</span>
          <input type="number" min={0} max={9}
            value={maxRivals === 99 ? "" : maxRivals} placeholder="any"
            onChange={(e) => setMaxRivals(e.target.value === "" ? 99 : Math.max(0, Math.min(9, Number(e.target.value))))}
            className="w-full bg-transparent font-mono text-slate-100 outline-none" />
        </label>
        <label className="rounded-lg bg-ink-800 px-1.5 py-1">
          <span className="text-slate-500">top-k</span>
          <input type="number" min={1} max={12} value={topK}
            onChange={(e) => setTopK(Math.max(1, Math.min(12, Number(e.target.value))))}
            className="w-full bg-transparent font-mono text-slate-100 outline-none" />
        </label>
      </div>

      <button onClick={run} disabled={busy} className="btn-primary mt-2 w-full justify-center">
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Target size={12} />}
        Find best zones
      </button>
      {surviving !== null && (
        <div className="mt-1.5 text-center text-[10px] text-slate-500">
          {surviving} of 649 zones passed your filters
        </div>
      )}

      {zones.length > 0 && (
        <div className="mt-2 space-y-1">
          {zones.map((z, i) => (
            <div key={z.h3}
              className="flex items-center gap-2 rounded-lg bg-ink-800 px-2 py-1.5 text-[11px]">
              <span className="text-[10px] font-bold text-amber-400">#{i + 1}</span>
              <span className="font-mono font-bold" style={{ color: z.color }}>{Math.round(z.overall)}</span>
              <span className="flex-1 truncate text-slate-300" title={`pop ${z.scores.population} acc ${z.scores.accessibility} comp ${z.scores.competition}`}>
                zone {z.h3.slice(-6)} <span className="text-slate-600">· {z.land_category}</span>
              </span>
              <button onClick={() => flyToSite(z.latitude, z.longitude, 13.5)}
                title="Fly there" className="text-accent-300 hover:text-accent-400 text-[10px]">✈</button>
              <button onClick={() => analyzeZone(z)}
                title="Analyse" className="text-mint-300 hover:text-mint-400 text-[10px]">🎯</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
