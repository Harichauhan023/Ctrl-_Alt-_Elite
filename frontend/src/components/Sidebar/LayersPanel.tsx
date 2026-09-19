import { useEffect, useState } from "react";
import { Flame } from "lucide-react";
import { api } from "../../services/api";
import { LAYER_COLORS, useAppStore } from "../../store/useAppStore";
import type { LayerInfo } from "../../types";

export default function LayersPanel() {
  const layerState = useAppStore((s) => s.layerState);
  const toggleLayer = useAppStore((s) => s.toggleLayer);
  const setLayerOpacity = useAppStore((s) => s.setLayerOpacity);
  const heatmapOn = useAppStore((s) => s.heatmapOn);
  const setHeatmapOn = useAppStore((s) => s.setHeatmapOn);
  const [catalog, setCatalog] = useState<LayerInfo[]>([]);

  useEffect(() => {
    api.layers().then((d) => setCatalog(d.layers)).catch(() => {});
  }, []);

  const info = (name: string) => catalog.find((c) => c.name === name);

  return (
    <div className="glass rounded-xl p-3">
      <div className="panel-title mb-2">Geospatial layers</div>
      <div className="space-y-1.5">
        {Object.keys(layerState).map((name) => {
          const st = layerState[name];
          const c = info(name);
          return (
            <div key={name} className="rounded-lg px-1 py-1 hover:bg-ink-800/60">
              <label className="flex cursor-pointer items-center gap-2 text-xs">
                <input type="checkbox" checked={!!st?.visible} onChange={() => toggleLayer(name)}
                  className="h-3.5 w-3.5 accent-sky-500" />
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: LAYER_COLORS[name] }} />
                <span className="flex-1 text-slate-200">{c?.label || name}</span>
                {c && <span className="text-[10px] text-slate-500">{c.count.toLocaleString()}</span>}
              </label>
              {st?.visible && (
                <input type="range" min={10} max={100} value={Math.round((st.opacity ?? 1) * 100)}
                  onChange={(e) => setLayerOpacity(name, Number(e.target.value) / 100)}
                  className="ml-7 mt-1 w-[70%]" />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-3 border-t border-ink-700 pt-3">
        <label className={`flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-xs font-semibold transition-colors ${
          heatmapOn ? "bg-accent-600/20 text-accent-300" : "text-slate-300 hover:bg-ink-800"}`}>
          <input type="checkbox" checked={heatmapOn} onChange={(e) => setHeatmapOn(e.target.checked)}
            className="h-3.5 w-3.5 accent-sky-500" />
          <Flame size={13} className={heatmapOn ? "text-amber-400" : "text-slate-500"} />
          Readiness heatmap (H3)
        </label>
        <p className="mt-1 px-2 text-[10px] text-slate-500">
          649 H3 res-8 zones scored live with your current weights.
        </p>
      </div>
    </div>
  );
}
