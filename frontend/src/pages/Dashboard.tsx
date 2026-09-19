import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Bot, Database, Hexagon, Map, Navigation, Users, Zap } from "lucide-react";
import { api } from "../services/api";
import { mapSingleton } from "../map/singleton";

const BAND_COLORS: Record<string, string> = {
  High: "#22c55e", Good: "#84cc16", Medium: "#f59e0b", Weak: "#f97316", Low: "#ef4444", Restricted: "#7f1d1d",
};

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
    api.health().then(setHealth).catch(() => {});
  }, []);

  const dist = stats?.ev_readiness_distribution;
  const bands: Array<[string, number]> = dist ? Object.entries(dist.bands as Record<string, number>) : [];
  const maxBand = Math.max(1, ...bands.map(([, v]) => v));

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="mx-auto max-w-6xl">
        <div className="mb-5 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Mission Control</h1>
            <p className="mt-0.5 text-xs text-slate-400">
              {stats?.study_area ?? "Rajkot"} · geospatial intelligence at a glance
            </p>
          </div>
          <button className="btn-primary" onClick={() => navigate("/")}>
            <Map size={13} /> Open Map Analysis
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Kpi icon={<Users size={15} />} label="Modelled population"
            value={stats ? (stats.total_modelled_population / 100000).toFixed(2) + " L" : "…"}
            sub="H3 res-9 demand grid" color="#38bdf8" />
          <Kpi icon={<Navigation size={15} />} label="Road network"
            value={stats ? `${stats.road_network_km.toLocaleString()} km` : "…"} sub="real OpenStreetMap" color="#e2e8f0" />
          <Kpi icon={<Zap size={15} />} label="EV competitors"
            value={stats?.competitors ?? "…"} sub="charging locations" color="#fbbf24" />
          <Kpi icon={<Hexagon size={15} />} label="Analysis zones"
            value={stats?.hotspot_cells ?? "…"} sub="H3 res-8 cells" color="#a78bfa" />
          <Kpi icon={<Activity size={15} />} label="Mean zone readiness"
            value={dist ? `${dist.mean}/100` : "…"} sub={`p90 = ${dist?.p90 ?? "…"}`} color="#34d399" />
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {/* readiness distribution */}
          <div className="glass rounded-xl p-4 lg:col-span-2">
            <div className="panel-title mb-3">Zone readiness distribution — EV Charging (default weights)</div>
            <div className="space-y-2">
              {bands.sort().map(([band, count]) => (
                <div key={band} className="flex items-center gap-3">
                  <span className="w-20 text-[11px] font-medium text-slate-300">{band}</span>
                  <div className="h-4 flex-1 overflow-hidden rounded bg-ink-800">
                    <div className="h-full rounded transition-all duration-700"
                      style={{ width: `${(count / maxBand) * 100}%`, background: BAND_COLORS[band] }} />
                  </div>
                  <span className="w-10 text-right font-mono text-[11px] text-slate-400">{count}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] text-slate-500">
              Every one of the {dist?.cells ?? "…"} hexagonal zones is scored with the same deterministic
              engine as a point site — the heatmap is just the engine run 649 times.
            </p>
          </div>

          {/* AI + data status */}
          <div className="space-y-3">
            <div className="glass rounded-xl p-4">
              <div className="panel-title mb-2 flex items-center gap-1.5"><Bot size={12} /> AI subsystem</div>
              <Row k="LLM providers" v={health?.ai?.providers_configured ?? 0} ok={health?.ai?.providers_configured > 0} />
              <Row k="RAG mode" v={health?.ai?.rag_mode ?? "…"} ok={health?.ai?.rag_mode === "semantic"} />
              <Row k="Embeddings" v="MiniLM 384-dim local" ok />
              <Row k="LLM calls made" v={health?.ai?.llm_calls ?? 0} ok />
              <Row k="Graceful fallbacks" v={health?.ai?.fallbacks ?? 0} ok />
              <p className="mt-2 text-[10px] leading-snug text-slate-500">
                No keys configured yet → the deterministic explainer is primary. Drop Gemini keys in
                <code className="text-slate-400"> .env </code> and the 4-provider failover activates instantly.
              </p>
            </div>
            <div className="glass rounded-xl p-4">
              <div className="panel-title mb-2 flex items-center gap-1.5"><Database size={12} /> Data layers</div>
              {health && Object.entries(health.layers_loaded as Record<string, number>).map(([k, v]) => (
                <Row key={k} k={k} v={v.toLocaleString()} ok />
              ))}
            </div>
          </div>
        </div>

        {/* top zones */}
        {dist?.top_cells?.length > 0 && (
          <div className="glass mt-4 rounded-xl p-4">
            <div className="panel-title mb-3">🏆 Highest-readiness zones (EV) — click to fly there</div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              {dist.top_cells.map((c: any, i: number) => (
                <button key={c.h3}
                  onClick={() => {
                    navigate("/");
                    setTimeout(() => mapSingleton.map?.flyTo({ center: [c.lng, c.lat], zoom: 13.5 }), 1400);
                  }}
                  className="flex items-center gap-2 rounded-lg bg-ink-800 px-3 py-2 text-left hover:bg-ink-700">
                  <span className="text-sm font-bold text-mint-400">#{i + 1}</span>
                  <span className="flex-1 font-mono text-[10px] text-slate-500">{c.h3.slice(-6)}</span>
                  <span className="text-sm font-bold text-mint-300">{c.overall}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Kpi({ icon, label, value, sub, color }: any) {
  return (
    <div className="glass rounded-xl p-3.5">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-slate-500">
        <span style={{ color }}>{icon}</span> {label}
      </div>
      <div className="mt-1 text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-[10px] text-slate-500">{sub}</div>
    </div>
  );
}

function Row({ k, v, ok }: { k: string; v: any; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between py-0.5 text-[11px]">
      <span className="text-slate-400">{k}</span>
      <span className={`font-semibold ${ok ? "text-mint-300" : "text-amber-300"}`}>{v}</span>
    </div>
  );
}
