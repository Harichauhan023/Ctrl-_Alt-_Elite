import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Crown, Loader2, Map } from "lucide-react";
import {
  Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar,
  RadarChart, ResponsiveContainer, Tooltip,
} from "recharts";
import { api } from "../services/api";
import { FACTOR_KEYS, FACTOR_META, useAppStore } from "../store/useAppStore";
import type { AnalysisResult } from "../types";
import { scoreColor } from "../components/Analysis/ScoreGauge";

const SITE_COLORS = ["#38bdf8", "#fbbf24", "#34d399", "#f472b6"];

export default function Compare() {
  const compareList = useAppStore((s) => s.compareList);
  const businessType = useAppStore((s) => s.businessType);
  const weights = useAppStore((s) => s.weights);
  const navigate = useNavigate();
  const [data, setData] = useState<{ results: AnalysisResult[]; winners: Record<string, string>; narrative: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (compareList.length < 2) return;
    setLoading(true);
    api.compare({
      points: compareList.map((a) => ({ name: a.name, latitude: a.latitude, longitude: a.longitude })),
      business_type: businessType,
      weights,
    })
      .then((d) => { setData(d); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [compareList, businessType, weights]);

  const radarData = useMemo(() => {
    if (!data) return [];
    return FACTOR_KEYS.map((k) => {
      const row: any = { factor: FACTOR_META[k].label };
      data.results.forEach((r) => { row[r.name!] = r.scores[k]; });
      return row;
    });
  }, [data]);

  if (compareList.length < 2) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="glass max-w-md rounded-xl p-8 text-center">
          <div className="text-4xl">⚖️</div>
          <h2 className="mt-3 text-lg font-bold">Nothing to compare yet</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            On the map, analyze at least two sites and press <b>Compare</b> on each —
            they'll appear here side by side with radar charts, factor winners and an
            auto-generated decision narrative.
          </p>
          <button className="btn-primary mx-auto mt-4" onClick={() => navigate("/")}>
            <Map size={13} /> Back to Map
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Site Comparison</h1>
            <p className="mt-0.5 text-xs text-slate-400">
              Same business, same weights, same math — honest side-by-side.
            </p>
          </div>
          <button className="btn-ghost" onClick={() => navigate("/")}><Map size={12} /> Map</button>
        </div>

        {loading && <div className="flex justify-center py-16"><Loader2 className="animate-spin text-accent-400" /></div>}
        {error && <div className="rounded-lg bg-danger-500/15 p-3 text-xs text-danger-400">⚠ {error}</div>}

        {data && !loading && (
          <div className="grid gap-4 lg:grid-cols-5">
            {/* radar */}
            <div className="glass rounded-xl p-4 lg:col-span-2">
              <div className="panel-title mb-2">Factor radar</div>
              <ResponsiveContainer width="100%" height={330}>
                <RadarChart data={radarData} outerRadius="72%">
                  <PolarGrid stroke="#243356" />
                  <PolarAngleAxis dataKey="factor" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  {data.results.map((r, i) => (
                    <Radar key={r.name} name={r.name!} dataKey={r.name!}
                      stroke={SITE_COLORS[i % 4]} fill={SITE_COLORS[i % 4]} fillOpacity={0.12} strokeWidth={2} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#0d1424", border: "1px solid #243356", borderRadius: 8, fontSize: 11 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* table */}
            <div className="glass rounded-xl p-4 lg:col-span-3">
              <div className="panel-title mb-3">Factor-by-factor · weight-adjusted view</div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-ink-700 text-left text-[10px] uppercase tracking-wide text-slate-500">
                      <th className="pb-2 pr-2">Factor</th>
                      {data.results.map((r, i) => (
                        <th key={r.name} className="pb-2 text-right" style={{ color: SITE_COLORS[i % 4] }}>
                          {r.name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(["overall", "ml", ...FACTOR_KEYS] as const).map((f) => {
                      const isOverall = f === "overall";
                      const isMl = f === "ml";
                      // ML winner: highest ml_prediction among sites that have one
                      const mlWinner = isMl
                        ? data.results.filter((r) => r.ml_prediction != null)
                            .sort((a, b) => (b.ml_prediction ?? 0) - (a.ml_prediction ?? 0))[0]?.name
                        : undefined;
                      return (
                        <tr key={f} className={`border-b border-ink-800 ${isOverall ? "font-bold" : ""}`}>
                          <td className="py-1.5 pr-2 text-slate-300">
                            {isOverall ? "⭐ Overall" : isMl
                              ? <span className="text-violet-300">🧠 ML prediction</span>
                              : FACTOR_META[f as keyof typeof FACTOR_META].label}
                          </td>
                          {data.results.map((r) => {
                            const v = isOverall ? r.overall_score : isMl
                              ? (r.ml_prediction != null ? r.ml_prediction.toFixed(1) : "—")
                              : r.scores[f as keyof typeof r.scores];
                            const win = isMl ? data.results.length > 1 && mlWinner === r.name : data.winners[f] === r.name;
                            return (
                              <td key={r.name} className={`py-1.5 text-right font-mono ${win ? "font-bold" : ""}`}
                                style={{ color: isMl ? (win ? "#c4b5fd" : "#a78bfa") : win ? "#6ee7b7" : "#cbd5e1" }}>
                                {v}{win && <Crown size={10} className={`ml-1 inline ${isMl ? "text-violet-300" : "text-mint-400"}`} />}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {data.results.some((r) => r.constraints.length > 0) && (
                <div className="mt-3 flex items-start gap-1.5 rounded-lg bg-danger-500/10 p-2 text-[11px] text-danger-400">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  {data.results.filter((r) => r.constraints.length > 0)
                    .map((r) => `${r.name}: ${r.constraints[0]}`).join(" · ")}
                </div>
              )}

              <div className="panel-title mb-2 mt-4">Decision narrative</div>
              <div className="space-y-1.5">
                {data.narrative.map((n, i) => (
                  <div key={i} className="rounded-lg bg-ink-800 px-3 py-2 text-[11px] leading-relaxed text-slate-300">
                    {n}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
