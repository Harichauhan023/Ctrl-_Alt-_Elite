import { RotateCcw, Scale } from "lucide-react";
import { FACTOR_KEYS, FACTOR_META, useAppStore, weightSum } from "../../store/useAppStore";

export default function WeightsPanel() {
  const weights = useAppStore((s) => s.weights);
  const setWeight = useAppStore((s) => s.setWeight);
  const normalizeWeights = useAppStore((s) => s.normalizeWeights);
  const resetWeights = useAppStore((s) => s.resetWeights);
  const sum = weightSum(weights);
  const ok = Math.abs(sum - 100) <= 5;

  return (
    <div className="glass rounded-xl p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="panel-title">Factor weights</div>
        <div className="flex items-center gap-1">
          <button onClick={resetWeights} title="Reset to business defaults"
            className="rounded-md p-1 text-slate-400 hover:bg-ink-700 hover:text-slate-200">
            <RotateCcw size={12} />
          </button>
          <button onClick={normalizeWeights} title="Normalize to 100%"
            className="rounded-md p-1 text-slate-400 hover:bg-ink-700 hover:text-slate-200">
            <Scale size={12} />
          </button>
        </div>
      </div>
      <div className="space-y-2.5">
        {FACTOR_KEYS.map((k) => (
          <div key={k}>
            <div className="mb-1 flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="h-2 w-2 rounded-sm" style={{ background: FACTOR_META[k].color }} />
                {FACTOR_META[k].label}
              </span>
              <span className="font-mono font-semibold text-slate-100">{weights[k]}%</span>
            </div>
            <input
              type="range" min={0} max={100} value={weights[k]}
              onChange={(e) => setWeight(k, Number(e.target.value))}
              className="w-full"
            />
          </div>
        ))}
      </div>
      <div className={`mt-2.5 rounded-md px-2 py-1.5 text-center text-[11px] font-semibold ${
        ok ? "bg-mint-500/15 text-mint-300" : "bg-danger-500/15 text-danger-400"}`}>
        Σ = {sum}% {ok ? "✓" : "— must be ~100% (auto-normalized server-side within ±5%)"}
      </div>
      <p className="mt-2 text-[10px] leading-snug text-slate-500">
        Drag sliders — the site score, heatmap and comparison update live with identical math everywhere.
      </p>
    </div>
  );
}
