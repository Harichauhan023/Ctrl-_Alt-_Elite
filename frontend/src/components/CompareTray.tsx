import { useNavigate } from "react-router-dom";
import { GitCompareArrows, X } from "lucide-react";
import { useAppStore } from "../store/useAppStore";
import { scoreColor } from "./Analysis/ScoreGauge";

export default function CompareTray() {
  const list = useAppStore((s) => s.compareList);
  const remove = useAppStore((s) => s.removeFromCompare);
  const navigate = useNavigate();
  if (list.length === 0) return null;

  return (
    <div className="glass absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 rounded-xl px-3 py-2">
      <GitCompareArrows size={14} className="text-accent-400" />
      {list.map((a) => (
        <span key={a.name}
          className="flex items-center gap-1.5 rounded-md bg-ink-800 px-2 py-1 text-[11px] font-medium text-slate-200">
          <span className="font-mono font-bold" style={{ color: scoreColor(a.overall_score, a.status) }}>
            {Math.round(a.overall_score)}
          </span>
          {a.name}
          <button onClick={() => remove(a.name!)} className="text-slate-500 hover:text-danger-400">
            <X size={11} />
          </button>
        </span>
      ))}
      <button className="btn-primary" disabled={list.length < 2} onClick={() => navigate("/compare")}>
        Compare ({list.length})
      </button>
    </div>
  );
}
