import { useNavigate } from "react-router-dom";
import { Brain, Database, Map as MapIcon, Radar } from "lucide-react";
import ChatBox from "../components/Assistant/ChatBox";
import MiniMap from "../components/Map/MiniMap";

export default function ChatHome() {
  const navigate = useNavigate();
  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-ink-950">
      {/* ambient backdrop */}
      <div className="pointer-events-none absolute inset-0 opacity-60" style={{
        background:
          "radial-gradient(900px 480px at 15% -10%, rgba(56,189,248,0.10), transparent 60%)," +
          "radial-gradient(800px 420px at 85% 110%, rgba(45,212,191,0.08), transparent 60%)",
      }} />

      <div className="relative mx-auto flex h-full w-full max-w-3xl flex-col px-4 pb-4 pt-3">
        {/* hero header */}
        <div className="mb-3 text-center">
          <div className="mb-1 flex items-center justify-center gap-2">
            <MapIcon size={18} className="text-accent-400" />
            <h1 className="text-lg font-bold tracking-tight text-slate-100">
              GeoReady-<span className="text-accent-400">AI</span>
              <span className="ml-2 rounded-full bg-ink-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">Rajkot pilot</span>
            </h1>
          </div>
          <p className="mx-auto max-w-xl text-[12px] leading-snug text-slate-400">
            Talk to the decision assistant. Every number comes from the deterministic engine + ML model;
            every answer is grounded by semantic top-k retrieval over our knowledge documents.
          </p>
          <div className="mt-2 flex items-center justify-center gap-1.5 text-[9.5px] text-slate-500">
            <span className="flex items-center gap-1 rounded-full bg-ink-800/80 px-2 py-0.5"><Database size={9} /> PostGIS / DuckDB spatial</span>
            <span className="flex items-center gap-1 rounded-full bg-ink-800/80 px-2 py-0.5"><Brain size={9} /> RandomForest · R² 0.96</span>
            <span className="flex items-center gap-1 rounded-full bg-ink-800/80 px-2 py-0.5"><Radar size={9} /> MiniLM RAG top-k</span>
          </div>
        </div>

        {/* live mini-map — the city is always one glance away */}
        <div className="mb-3 h-40 shrink-0 md:h-44">
          <MiniMap className="h-full w-full" />
        </div>

        {/* chat */}
        <div className="panel flex min-h-0 flex-1 flex-col rounded-2xl p-4">
          <ChatBox variant="page" />
        </div>

        <div className="mt-2 text-center">
          <button onClick={() => navigate("/map")}
            className="text-[11px] font-semibold text-accent-300 hover:text-accent-200">
            → Jump straight to the interactive map
          </button>
        </div>
      </div>
    </div>
  );
}
