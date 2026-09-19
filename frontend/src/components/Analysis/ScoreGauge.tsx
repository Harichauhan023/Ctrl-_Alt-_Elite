export function scoreColor(score: number, status?: string) {
  if (status === "NOT_SUITABLE") return "#ef4444";
  if (score >= 80) return "#22c55e";
  if (score >= 65) return "#84cc16";
  if (score >= 50) return "#f59e0b";
  if (score >= 35) return "#f97316";
  return "#ef4444";
}

/** Semicircular gauge for the overall readiness score. */
export default function ScoreGauge({ score, status }: { score: number; status?: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  const angle = (clamped / 100) * 180;
  const r = 65;
  const cx = 80, cy = 78;
  const rad = (a: number) => ((180 - a) * Math.PI) / 180;
  const arc = (from: number, to: number) => {
    const large = to - from > 180 ? 1 : 0;
    return `M ${cx + r * Math.cos(rad(from))} ${cy - r * Math.sin(rad(from))}
            A ${r} ${r} 0 ${large} 1 ${cx + r * Math.cos(rad(to))} ${cy - r * Math.sin(rad(to))}`;
  };
  const color = scoreColor(clamped, status);

  return (
    <div className="relative mx-auto w-40">
      <svg viewBox="0 0 160 88" className="w-full">
        <path d={arc(0, 180)} fill="none" stroke="#1a2540" strokeWidth={11} strokeLinecap="round" />
        {clamped > 0.5 && (
          <path d={arc(0, angle)} fill="none" stroke={color} strokeWidth={11} strokeLinecap="round" />
        )}
        <text x={cx} y={cy - 12} textAnchor="middle" fill={color}
          style={{ fontSize: 30, fontWeight: 800, fontFamily: "Inter" }}>
          {Math.round(clamped)}
        </text>
        <text x={cx} y={cy + 2} textAnchor="middle" fill="#64748b" style={{ fontSize: 9, fontFamily: "Inter" }}>
          / 100 READINESS
        </text>
      </svg>
      {status === "NOT_SUITABLE" && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-danger-500/20 px-2 py-0.5 text-[10px] font-bold text-danger-400">
          ⛔ NOT SUITABLE — hard constraint
        </div>
      )}
    </div>
  );
}
