import { Shapes, Trash2 } from "lucide-react";
import { useAppStore } from "../../store/useAppStore";

const MIX_COLORS: Record<string, string> = {
  commercial: "#d97706", mixed_use: "#8b5cf6", industrial: "#57534e", residential: "#0e7490",
  agricultural: "#4d7c0f", protected: "#b91c1c", unknown: "#334155",
};

/** Results of draw-a-polygon district analysis. */
export default function AreaPanel() {
  const result = useAppStore((s) => s.polygonResult);

  if (!result) {
    return (
      <div className="rounded-xl border border-dashed border-ink-600 p-4 text-center">
        <Shapes size={20} className="mx-auto text-slate-500" />
        <div className="mt-2 text-xs font-semibold text-slate-300">No area drawn yet</div>
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
          Press <b className="text-slate-300">✏️ Draw area</b> on the map toolbar, click 3+ points,
          then double-click (or Enter) to finish. The engine aggregates population, roads,
          competitors, land mix and zone readiness inside your shape.
        </p>
      </div>
    );
  }

  const mixTotal = Object.values(result.land_use_mix).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold text-slate-100">
          District analysis <span className="text-slate-500 font-normal">· {result.business_label}</span>
        </div>
        <button onClick={() => useAppStore.getState().setPolygon(null, null)}
          className="text-slate-500 hover:text-danger-400" title="Clear area">
          <Trash2 size={13} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-1.5 text-center">
        <Stat label="Area" value={`${result.area_km2} km²`} />
        <Stat label="Population" value={result.population.toLocaleString()} accent />
        <Stat label="Roads" value={`${result.road_km} km`} />
        <Stat label="Competitors" value={String(result.competitors)} />
        <Stat label="Zones" value={String(result.zones.count)} />
        <Stat label="Mean readiness" value={String(result.zones.readiness_mean)} accent />
      </div>

      <div>
        <div className="panel-title mb-1.5">Zone readiness band mix</div>
        <div className="flex h-3.5 w-full overflow-hidden rounded-full">
          {(["High", "Good", "Medium", "Weak", "Low", "Restricted"] as const).map((b) => {
            const n = result.zones.bands[b] ?? 0;
            if (!n) return null;
            const colors: Record<string, string> = { High: "#22c55e", Good: "#84cc16", Medium: "#f59e0b", Weak: "#f97316", Low: "#ef4444", Restricted: "#7f1d1d" };
            return <div key={b} title={`${b}: ${n}`} style={{ width: `${(n / result.zones.count) * 100}%`, background: colors[b] }} />;
          })}
        </div>
        <div className="mt-1 flex flex-wrap gap-2 text-[9.5px] text-slate-500">
          {Object.entries(result.zones.bands).map(([b, n]) => <span key={b}>{b} {n}</span>)}
        </div>
      </div>

      <div>
        <div className="panel-title mb-1.5">Land-use mix (by zone)</div>
        <div className="space-y-1">
          {Object.entries(result.land_use_mix).sort((a, b) => b[1] - a[1]).map(([cat, n]) => (
            <div key={cat} className="flex items-center gap-2 text-[11px]">
              <span className="w-20 truncate text-slate-400">{cat}</span>
              <div className="h-2 flex-1 overflow-hidden rounded bg-ink-800">
                <div className="h-full rounded" style={{ width: `${(n / mixTotal) * 100}%`, background: MIX_COLORS[cat] ?? "#334155" }} />
              </div>
              <span className="w-6 text-right font-mono text-slate-400">{n}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        {result.verdict.map((v, i) => (
          <div key={i} className="rounded-lg bg-ink-800 px-2.5 py-1.5 text-[11px] leading-snug text-slate-300">{v}</div>
        ))}
      </div>

      <p className="text-[9.5px] italic text-slate-600">{result.method}</p>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg bg-ink-800/80 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`truncate text-sm font-bold ${accent ? "text-accent-300" : "text-slate-100"}`}>{value}</div>
    </div>
  );
}
