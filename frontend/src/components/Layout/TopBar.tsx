import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { BarChart3, BookOpen, GitCompareArrows, LayoutDashboard, Map, MessagesSquare, Radar } from "lucide-react";
import { api } from "../../services/api";
import { useAppStore } from "../../store/useAppStore";

const NAV = [
  { to: "/", label: "Chat", icon: MessagesSquare },
  { to: "/map", label: "Map", icon: Map },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/compare", label: "Compare", icon: GitCompareArrows },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
];

export default function TopBar() {
  const { pathname } = useLocation();
  const compareList = useAppStore((s) => s.compareList);
  const [health, setHealth] = useState<any | null>(null);

  useEffect(() => {
    const tick = () => api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="z-20 flex h-12 shrink-0 items-center gap-4 border-b border-ink-700 bg-ink-900/95 px-4">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-600">
          <Radar size={16} className="text-white" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-tight">GeoReady-AI</div>
          <div className="text-[10px] text-slate-500">Site Readiness Analyzer · Rajkot</div>
        </div>
      </div>

      <nav className="ml-4 flex items-center gap-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              pathname === to
                ? "bg-ink-700 text-accent-300"
                : "text-slate-400 hover:bg-ink-800 hover:text-slate-200"
            }`}
          >
            <Icon size={14} />
            {label}
            {to === "/compare" && compareList.length > 0 && (
              <span className="ml-1 rounded-full bg-accent-600 px-1.5 text-[10px] font-bold text-white">
                {compareList.length}
              </span>
            )}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2 text-[10px]">
        <span className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1 text-slate-400">
          Bit N Build '26 · PS-2
        </span>
        <span className="flex items-center gap-1.5 rounded-md border border-ink-600 bg-ink-800 px-2 py-1"
          title={health ? `backend ${health.status}` : ""}>
          <span
            className={`live-dot h-1.5 w-1.5 rounded-full ${
              health === null ? "bg-amber-400" : health.status !== "down" ? "bg-mint-400" : "bg-danger-400"
            }`}
          />
          <span className="text-slate-300">
            API {health === null ? "…" : health.status === "down" ? "down" : "live"}
          </span>
          {health?.database?.mode && (
            <span className="text-slate-500">· {health.database.mode}</span>
          )}
          {health?.ai?.rag_mode && health.ai.rag_mode !== "off" && (
            <span className="text-teal-300/80">· {health.ai.rag_mode}</span>
          )}
        </span>
      </div>
    </header>
  );
}
