import { useEffect, useMemo, useState } from "react";
import { BookOpen, Brain, Loader2, Search, Tag } from "lucide-react";
import { api } from "../services/api";

type Chunk = { title: string; text: string; tags: string[]; score: number; source?: string };

const SUGGESTIONS = [
  "competition distance decay",
  "NOT_SUITABLE constraints",
  "EV charging playbook",
  "is the population data real",
  "what ML model do you use",
  "H3 resolution 8",
  "Rajkot growth directions",
  "catchment accuracy",
  "glossary: feature importance",
  "what-if ghost rivals",
];

export default function Knowledge() {
  const [q, setQ] = useState("site readiness scoring");
  const [k, setK] = useState(8);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<string>("semantic");
  const [total, setTotal] = useState(0);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [error, setError] = useState<string | null>(null);

  const search = async (query: string, top: number) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.ragSearch(query || "site readiness scoring", top);
      setMode(r.mode);
      setTotal(r.total_docs);
      setChunks(r.chunks);
    } catch (e: any) {
      setError(e.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void search(q, k); /* initial load */ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k]);

  const topTags = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of chunks) for (const t of c.tags) map.set(t, (map.get(t) ?? 0) + 1);
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12).map(([t]) => t);
  }, [chunks]);

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center gap-2">
          <BookOpen size={18} className="text-accent-400" />
          <h1 className="text-xl font-bold tracking-tight">Knowledge Explorer</h1>
          <span className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1 text-[10px] text-slate-400">
            RAG corpus · <b className="text-accent-300">{total || "…"}</b> chunks ·{" "}
            <b className="text-teal-300">{mode}</b> mode
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          This is the exact retrieval corpus the AI assistant and explainer read from — real Markdown
          documents in <code className="text-accent-300">rag/documents/</code>, chunked, embedded with MiniLM
          (384-dim), stored in the spatial DB and ranked by vector cosine similarity (mode shown above). Retrieval supplies <i>context</i>, never numbers.
        </p>

        {/* search bar */}
        <div className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search(q, k)}
              placeholder="Semantic search across methodology, playbooks, Rajkot knowledge, FAQ…"
              className="w-full rounded-lg border border-ink-600 bg-ink-800 py-2.5 pl-9 pr-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent-500"
            />
          </div>
          <select value={k} onChange={(e) => setK(+e.target.value)}
            className="rounded-lg border border-ink-600 bg-ink-800 px-2 text-xs text-slate-300 outline-none">
            {[4, 6, 8, 12, 20].map((n) => <option key={n} value={n}>top {n}</option>)}
          </select>
          <button className="btn-primary px-4 py-2 text-sm" onClick={() => search(q, k)} disabled={loading}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : "Search"}
          </button>
        </div>

        {/* suggestion chips */}
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button key={s}
              onClick={() => { setQ(s); void search(s, k); }}
              className={`rounded-full border px-2.5 py-1 text-[10px] transition-colors ${
                q === s ? "border-accent-500/60 bg-accent-600/20 text-accent-300"
                        : "border-ink-600 bg-ink-800 text-slate-400 hover:text-slate-200"}`}>
              {s}
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-3 rounded-lg bg-danger-500/15 p-3 text-xs text-danger-400">⚠ {error}</div>
        )}

        {topTags.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
            <Tag size={10} /> matched tags:
            {topTags.map((t) => (
              <span key={t} className="rounded bg-ink-800 px-1.5 py-0.5 text-slate-400">{t}</span>
            ))}
          </div>
        )}

        {/* results */}
        <div className="mt-3 space-y-2.5 pb-8">
          {chunks.map((c, i) => {
            const pct = Math.min(100, Math.max(2, c.score * 100));
            return (
              <div key={i} className="glass rounded-xl p-4 hover:border-accent-500/40">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-bold text-slate-100">
                      <span className="mr-2 font-mono text-[10px] text-slate-500">#{i + 1}</span>
                      {c.title}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1">
                      {c.tags.map((t) => (
                        <span key={t} className="rounded bg-ink-800 px-1.5 py-0.5 text-[9px] text-slate-500">{t}</span>
                      ))}
                      {c.source && (
                        <span className="rounded bg-accent-600/15 px-1.5 py-0.5 font-mono text-[8.5px] text-accent-300">
                          {c.source.replace("rag/documents/", "📄 ")}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="w-32 shrink-0 text-right">
                    <div className="font-mono text-xs font-bold text-teal-300">{c.score.toFixed(3)}</div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-ink-900">
                      <div className="h-full rounded-full bg-gradient-to-r from-teal-600 to-teal-400"
                        style={{ width: `${pct}%` }} />
                    </div>
                    <div className="mt-0.5 text-[8.5px] text-slate-600">cosine similarity</div>
                  </div>
                </div>
                <p className="mt-2 whitespace-pre-line text-[11.5px] leading-relaxed text-slate-300">{c.text}</p>
              </div>
            );
          })}
          {!loading && chunks.length === 0 && !error && (
            <div className="rounded-xl border border-dashed border-ink-600 p-8 text-center text-xs text-slate-500">
              No chunks matched — try a different phrasing.
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 border-t border-ink-700 pt-3 pb-6 text-[10px] text-slate-500">
          <Brain size={11} className="text-accent-400" />
          Design principle: the deterministic engine computes every score; this corpus only
          grounds explanations &amp; the assistant's replies — and every chunk names its source document.
        </div>
      </div>
    </div>
  );
}
