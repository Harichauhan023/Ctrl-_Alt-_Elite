import { useAppStore } from "../../store/useAppStore";

export default function BusinessSelect() {
  const businessType = useAppStore((s) => s.businessType);
  const businessTypes = useAppStore((s) => s.businessTypes);
  const setBusinessType = useAppStore((s) => s.setBusinessType);
  const current = businessTypes.find((b) => b.key === businessType);

  return (
    <div className="glass rounded-xl p-3">
      <div className="panel-title mb-2">Business type</div>
      <select
        value={businessType}
        onChange={(e) => setBusinessType(e.target.value)}
        className="w-full rounded-lg border border-ink-600 bg-ink-800 px-2.5 py-2 text-xs font-semibold text-slate-100 outline-none focus:border-accent-500"
      >
        {businessTypes.length === 0 && <option value="EV_CHARGING">EV Charging Station</option>}
        {businessTypes.map((b) => (
          <option key={b.key} value={b.key}>{b.label}</option>
        ))}
      </select>
      {current && (
        <p className="mt-2 text-[11px] leading-snug text-slate-400">{current.description}</p>
      )}
      {current && (
        <div className="mt-2 flex items-center gap-1.5 text-[10px]">
          <span className="rounded bg-ink-700 px-1.5 py-0.5 text-slate-300">
            competition: {current.competition_polarity === "attract" ? "📈 cluster = good" : "📉 cluster = bad"}
          </span>
        </div>
      )}
    </div>
  );
}
