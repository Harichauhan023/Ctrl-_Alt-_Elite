import { FACTOR_KEYS, FACTOR_META } from "../../store/useAppStore";
import type { FactorScores } from "../../types";

export default function FactorBars({ scores, weights }: { scores: FactorScores; weights: FactorScores }) {
  return (
    <div className="space-y-2">
      {FACTOR_KEYS.map((k) => (
        <div key={k}>
          <div className="mb-0.5 flex items-center justify-between text-[11px]">
            <span className="text-slate-300">{FACTOR_META[k].label}</span>
            <span className="font-mono text-slate-100">
              {Math.round(scores[k])}
              <span className="ml-1.5 text-[10px] text-slate-500">w {Math.round(weights[k] * 100)}%</span>
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-ink-700">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.max(2, scores[k])}%`, background: FACTOR_META[k].color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
