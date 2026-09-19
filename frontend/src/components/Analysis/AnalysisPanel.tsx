import { useEffect, useRef, useState } from "react";
import {
  BarChart3, Brain, Crosshair, Download, FlaskConical, GitCompareArrows, Loader2,
  MapPinned, MapPinPlus, Printer, Sparkles, Trash2,
} from "lucide-react";
import { api } from "../../services/api";
import { printReport } from "../../services/printReport";
import { useAnalysis } from "../../services/useAnalysis";
import { useAppStore } from "../../store/useAppStore";
import type { AnalysisResult, MlInsights } from "../../types";
import AIExplanation from "./AIExplanation";
import FactorBars from "./FactorBars";
import ScoreGauge, { scoreColor } from "./ScoreGauge";

let mlCache: { data: MlInsights | null; at: number } = { data: null, at: 0 };

/** Fetches /api/ml/insights once (module-level cache). */
function useMlInsights() {
  const [data, setData] = useState<MlInsights | null>(mlCache.data);
  const mounted = useRef(false);
  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    if (mlCache.data && Date.now() - mlCache.at < 600_000) { setData(mlCache.data); return; }
    api.mlInsights().then((d) => { mlCache = { data: d, at: Date.now() }; setData(d); }).catch(() => {});
  }, []);
  return data;
}

export default function AnalysisPanel({ docked }: { docked?: boolean }) {
  const analysis = useAppStore((s) => s.analysis);
  const analyzing = useAppStore((s) => s.analyzing);
  const error = useAppStore((s) => s.analysisError);
  const catchment = useAppStore((s) => s.catchment);
  const catchmentOn = useAppStore((s) => s.catchmentOn);
  const explanation = useAppStore((s) => s.explanation);
  const explaining = useAppStore((s) => s.explaining);
  const ghosts = useAppStore((s) => s.ghostCompetitors);
  const drawMode = useAppStore((s) => s.drawMode);
  const businessTypes = useAppStore((s) => s.businessTypes);
  const { refreshCatchment } = useAnalysis();
  const [question, setQuestion] = useState("");
  const [allBiz, setAllBiz] = useState<Record<string, AnalysisResult> | null>(null);
  const [allBusy, setAllBusy] = useState(false);
  const ml = useMlInsights();

  if (!analysis && !analyzing && !error) {
    return (
      <div className={docked ? "p-4" : "glass absolute right-3 top-14 z-10 w-80 rounded-xl p-4"}>
        <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
          <Crosshair size={15} className="text-accent-400" /> No site selected
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-slate-400">
          Click anywhere on the map — or pick a candidate marker — to compute a
          <b className="text-slate-200"> 0–100 Site Readiness Score</b> from the five geospatial factors.
        </p>
        <ul className="mt-2 space-y-1 text-[11px] text-slate-500">
          <li>🔥 Toggle the H3 readiness heatmap from the left panel</li>
          <li>⚖️ Drag weight sliders — scores recompute live</li>
          <li>✨ Ask the AI why a site scored what it did</li>
          <li>🌊 Try the river flood pocket near the old city…</li>
        </ul>
      </div>
    );
  }

  const metrics = analysis?.details || {};

  return (
    <div className={docked
      ? "flex flex-col gap-3 p-4"
      : "glass absolute bottom-3 right-3 top-14 z-10 flex w-[380px] flex-col gap-3 overflow-y-auto rounded-xl p-4"}>
      {analyzing && (
        <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-300">
          <Loader2 size={16} className="animate-spin text-accent-400" /> Scoring location…
        </div>
      )}
      {error && <div className="rounded-lg bg-danger-500/15 p-3 text-xs text-danger-400">⚠ {error}</div>}

      {analysis && !analyzing && (
        <>
          <div>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-bold leading-tight text-slate-100">
                  {analysis.name || "Candidate pin"}
                </div>
                <div className="mt-0.5 font-mono text-[10px] text-slate-500">
                  {analysis.latitude.toFixed(5)}, {analysis.longitude.toFixed(5)} · {analysis.business_label}
                </div>
              </div>
              <span className="rounded-md px-2 py-1 text-[10px] font-bold"
                style={{ background: `${scoreColor(analysis.overall_score, analysis.status)}22`,
                         color: scoreColor(analysis.overall_score, analysis.status) }}>
                {(analysis.status ?? "").replaceAll("_", " ")}
              </span>
            </div>
          </div>

          <ScoreGauge score={analysis.overall_score} status={analysis.status} />

          {/* ── ML visualization (§38): learned model beside deterministic rules ── */}
          {analysis.ml_available && analysis.ml_prediction != null && (
            <div className="rounded-xl border border-violet-500/25 bg-violet-500/5 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-violet-300">
                <Brain size={10} /> ML prediction (RandomForest)
                {ml?.metrics && (
                  <span className="ml-auto rounded bg-ink-800 px-1.5 py-0.5 font-mono text-[9px] text-slate-400"
                    title={`Trained on ${ml.n_samples?.toLocaleString()} synthetic sites · held-out 20%`}>
                    R² {ml.metrics.r2} · MAE ±{ml.metrics.mae}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <div className="text-[9px] uppercase tracking-wide text-slate-500">Rules engine</div>
                  <div className="text-xl font-bold text-slate-100">{analysis.overall_score.toFixed(1)}</div>
                </div>
                <div className="flex-1">
                  <div className="text-[9px] uppercase tracking-wide text-violet-400">ML model</div>
                  <div className="text-xl font-bold text-violet-300">{analysis.ml_prediction.toFixed(1)}</div>
                </div>
                <div className="flex-1 text-right">
                  <div className="text-[9px] uppercase tracking-wide text-slate-500">Δ agreement</div>
                  <div className={`text-lg font-bold ${
                    Math.abs(analysis.ml_prediction - analysis.overall_score) <= 5 ? "text-mint-300" : "text-amber-300"}`}>
                    {(analysis.ml_prediction - analysis.overall_score) >= 0 ? "+" : ""}
                    {(analysis.ml_prediction - analysis.overall_score).toFixed(1)}
                  </div>
                </div>
              </div>
              {/* agreement bar: rules vs ML positioned on one axis */}
              <div className="relative mt-2 h-2 rounded-full bg-ink-900">
                <div className="absolute top-1/2 h-0.5 w-full -translate-y-1/2 rounded bg-ink-700" />
                <div className="absolute top-1/2 h-2 w-0.5 -translate-y-1/2 rounded bg-slate-100"
                  style={{ left: `calc(${Math.min(100, Math.max(0, analysis.overall_score))}% - 1px)` }}
                  title={`Rules ${analysis.overall_score.toFixed(0)}`} />
                <div className="absolute top-1/2 h-2.5 w-0.5 -translate-y-1/2 rounded bg-violet-400"
                  style={{ left: `calc(${Math.min(100, Math.max(0, analysis.ml_prediction))}% - 1px)` }}
                  title={`ML ${analysis.ml_prediction.toFixed(0)}`} />
              </div>
              {ml?.feature_importance && (
                <div className="mt-2.5">
                  <div className="mb-1 text-[9px] font-bold uppercase tracking-wide text-slate-500">
                    What the model weighs most
                  </div>
                  <div className="space-y-1">
                    {ml.feature_importance.slice(0, 5).map((f) => (
                      <div key={f.name} className="flex items-center gap-1.5 text-[9.5px]">
                        <span className="w-40 truncate font-mono text-slate-400">
                          {f.name.replaceAll("_", " ")}
                        </span>
                        <span className="h-1 flex-1 overflow-hidden rounded-full bg-ink-800">
                          <span className="block h-full rounded-full bg-violet-500/80"
                            style={{ width: `${Math.min(100, f.importance / (ml.feature_importance?.[0]?.importance || 1) * 100)}%` }} />
                        </span>
                        <span className="w-8 text-right font-mono text-slate-500">{f.importance.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <p className="mt-2 text-[9px] leading-snug text-slate-500">
                ML read from the same 13 engineered features — <b className="text-slate-400">weight sliders do NOT
                move it</b>; it is an independent cross-check of the deterministic score (§38 rule).
              </p>
            </div>
          )}

          {analysis.constraints.length > 0 && (
            <div className="rounded-lg border border-danger-500/40 bg-danger-500/10 p-2.5">
              {analysis.constraints.map((c, i) => (
                <div key={i} className="text-[11px] font-semibold leading-snug text-danger-400">⛔ {c}</div>
              ))}
            </div>
          )}

          <div>
            <div className="panel-title mb-2">Score breakdown</div>
            <FactorBars scores={analysis.scores} weights={analysis.weights} />
          </div>

          <div className="grid grid-cols-2 gap-1.5 text-[11px]">
            <Metric label="Pop ≤1km" value={metrics.population?.population_within_1km?.toLocaleString()} />
            <Metric label="Major road" value={`${metrics.accessibility?.nearest_major_road_km ?? "—"} km`} />
            <Metric label="Comp ≤1km / ≤3km"
              value={`${metrics.competition?.competitors_within_1km ?? 0} / ${metrics.competition?.competitors_within_3km ?? 0}`} />
            <Metric label="Land use" value={metrics.land_use?.land_use_category} />
            <Metric label="Risk" value={metrics.environment?.risk_level ?? "low"} />
            <Metric label="Road density" value={`${metrics.accessibility?.road_density_km_per_km2 ?? "—"} km/km²`} />
          </div>

          {(analysis.reasons.length > 0 || analysis.risks.length > 0) && (
            <div className="space-y-1">
              {analysis.reasons.map((r, i) => (
                <div key={`r${i}`} className="rounded bg-mint-500/10 px-2 py-1 text-[11px] text-mint-300">✔ {r}</div>
              ))}
              {analysis.risks.map((r, i) => (
                <div key={`k${i}`} className="rounded bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300">⚠ {r}</div>
              ))}
            </div>
          )}

          {/* what-if scenario: ghost competitors */}
          <div className="rounded-xl border border-orange-500/25 bg-orange-500/5 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-orange-300">
              <FlaskConical size={10} /> What-if scenario
            </div>
            {ghosts.length > 0 && (
              <div className="mb-1.5 max-h-20 space-y-1 overflow-y-auto">
                {ghosts.map((g, i) => (
                  <div key={i} className="flex items-center justify-between rounded bg-ink-800 px-2 py-1">
                    <span className="font-mono text-[10px] text-orange-300">
                      🧪 rival {i + 1} · {g.lat.toFixed(4)}, {g.lng.toFixed(4)}
                    </span>
                    <button onClick={() => useAppStore.getState().removeGhost(i)}
                      className="text-slate-500 hover:text-danger-400" title="Remove rival">
                      <Trash2 size={10} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-1.5">
              <button
                className={`btn-ghost ${drawMode === "ghost" ? "!bg-orange-500/30 text-orange-300" : ""}`}
                onClick={() => useAppStore.getState().setDrawMode(drawMode === "ghost" ? false : "ghost")}>
                <MapPinPlus size={12} />
                {drawMode === "ghost" ? "Cancel drop" : ghosts.length ? "Drop another rival" : "Drop a rival"}
              </button>
              {ghosts.length > 0 && (
                <button className="btn-ghost" onClick={() => useAppStore.getState().clearGhosts()}>
                  <Trash2 size={12} /> Clear
                </button>
              )}
            </div>
            <p className="mt-1.5 text-[9.5px] leading-snug text-slate-500">
              Simulated rivals are fed into the <b className="text-slate-400">competition factor</b> of the same
              deterministic engine — watch the score react honestly, above.
            </p>
          </div>

          {/* all business types at this pin */}
          <div className="rounded-xl border border-ink-600 p-3">
            <button
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-ink-800 px-2 py-2 text-[11px] font-semibold text-accent-300 hover:bg-ink-700 disabled:opacity-50"
              disabled={allBusy}
              onClick={async () => {
                setAllBusy(true);
                try {
                  const r = await api.analyzeAll({
                    latitude: analysis.latitude,
                    longitude: analysis.longitude,
                    extra_competitors: ghosts.map((g) => ({ latitude: g.lat, longitude: g.lng })),
                  });
                  setAllBiz(r.results);
                } finally { setAllBusy(false); }
              }}>
              {allBusy ? <Loader2 size={11} className="animate-spin" /> : <BarChart3 size={11} />}
              {allBiz ? "Re-score all business types" : "Score all business types here"}
            </button>
            {allBiz && (
              <div className="mt-2 space-y-1.5">
                {Object.entries(allBiz)
                  .sort((a, b) => b[1].overall_score - a[1].overall_score)
                  .map(([key, r]) => {
                    const label = businessTypes.find((b) => b.key === key)?.label ?? r.business_label;
                    const c = scoreColor(r.overall_score, r.status);
                    return (
                      <div key={key} className="group">
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-slate-300">{label}</span>
                          <span className="font-mono font-bold" style={{ color: c }}>{Math.round(r.overall_score)}</span>
                          {r.ml_prediction != null && (
                            <span className="font-mono text-[9px] text-violet-300" title="ML prediction">
                              ML {Math.round(r.ml_prediction)}
                            </span>
                          )}
                        </div>
                        <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-ink-900">
                          <div className="h-full rounded-full transition-all"
                            style={{ width: `${r.overall_score}%`, background: c }} />
                        </div>
                      </div>
                    );
                  })}
                <p className="text-[9px] text-slate-600">Same pin, identical engine, six business lenses.</p>
              </div>
            )}
          </div>

          {/* actions */}
          <div className="flex flex-wrap gap-1.5">
            <button className="btn-primary" onClick={async () => {
              useAppStore.getState().setExplaining(true);
              try {
                const ex = await api.explain(analysis, question || undefined);
                useAppStore.getState().setExplanation(ex);
              } finally { useAppStore.getState().setExplaining(false); }
            }} disabled={explaining}>
              {explaining ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} Explain
            </button>
            <button className={`btn-ghost ${catchmentOn ? "!bg-accent-600/30 text-accent-300" : ""}`}
              onClick={async () => {
                const next = !catchmentOn;
                useAppStore.getState().setCatchmentOn(next);
                if (next && !catchment) await refreshCatchment();
              }}>
              <MapPinned size={12} /> Catchment
            </button>
            <button className="btn-ghost" onClick={() => useAppStore.getState().addToCompare(analysis)}>
              <GitCompareArrows size={12} /> Compare
            </button>
            <button className="btn-ghost" title="Download JSON report"
              onClick={async () => {
                const rep = await api.report(analysis, catchment, explanation?.explanation);
                const blob = new Blob([JSON.stringify(rep, null, 2)], { type: "application/json" });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = `geoready_${(analysis.name || "site").replaceAll(" ", "_")}.json`;
                a.click(); URL.revokeObjectURL(a.href);
              }}>
              <Download size={12} /> JSON
            </button>
            <button className="btn-mint" onClick={() => printReport(analysis, catchment, explanation)}>
              <Printer size={12} /> PDF / Print
            </button>
          </div>

          {/* catchment */}
          {catchmentOn && catchment && (
            <div className="rounded-xl border border-ink-600 p-3">
              <div className="panel-title mb-2">Travel-shed catchment</div>
              <div className="grid grid-cols-3 gap-1.5">
                {catchment.catchments.map((c) => (
                  <div key={c.minutes} className="rounded-lg bg-ink-800 p-2 text-center">
                    <div className="text-[10px] font-bold text-accent-300">{c.minutes} min</div>
                    <div className="text-sm font-bold text-slate-100">
                      {c.reachable_population >= 1000 ? `${(c.reachable_population / 1000).toFixed(1)}k` : c.reachable_population}
                    </div>
                    <div className="text-[9px] text-slate-500">people · {c.competitors_in_range} comp</div>
                  </div>
                ))}
              </div>
              <p className="mt-1.5 text-[9.5px] italic text-slate-500">{catchment.method}</p>
            </div>
          )}

          {/* AI question */}
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Optional: ask AI a question… (e.g. “what's the biggest risk?”)"
            className="w-full rounded-lg border border-ink-600 bg-ink-800 px-2.5 py-2 text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent-500"
          />

          {explanation && <AIExplanation data={explanation} />}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-lg bg-ink-800/80 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="truncate font-semibold text-slate-200">{value ?? "—"}</div>
    </div>
  );
}
