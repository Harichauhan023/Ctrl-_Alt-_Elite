import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, BookOpen, Bot, FileText, GitCompareArrows, Loader2, MapPin, Send, Sparkles, Target } from "lucide-react";
import { flyToSite } from "../../map/singleton";
import { api } from "../../services/api";
import { useAppStore } from "../../store/useAppStore";
import type { ChatMsg } from "../../types";

export const QUICK_PROMPTS = [
  "Recommend top 5 zones for EV charging",
  "How is Kalawad for an EV charger?",
  "Compare Old City vs Greenland for retail",
  "Best areas for a clinic with no competitors nearby",
  "Is the population data real or synthetic?",
  "What ML model do you use and how accurate is it?",
  "What does NOT_SUITABLE mean?",
];

/** Typewriter reveal for the newest assistant message (landing page feel). */
function TypeText({ text, onDone }: { text: string; onDone: () => void }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) { onDone(); return; }
    const step = text.length > 400 ? 18 : 9;
    const t = setTimeout(() => setN((v) => Math.min(v + step, text.length)), 12);
    return () => clearTimeout(t);
  }, [n, text, onDone]);
  return (
    <div className="whitespace-pre-wrap">
      {text.slice(0, n)}
      {n < text.length && <span className="animate-pulse text-accent-400">▍</span>}
    </div>
  );
}

export default function ChatBox({ variant }: { variant: "dock" | "page" }) {
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    { role: "assistant",
      text: variant === "page"
        ? "👋 Welcome to GeoReady-AI. Ask me anything about site selection in Rajkot — I answer from a real knowledge base (semantic top-k retrieval over 63 document chunks) and I drive the live scoring engine: zone recommendations, site analysis, comparisons, what-ifs."
        : "👋 I'm the GeoReady Assistant. I drive the real scoring engine — ask me to recommend zones, analyse named sites, compare locations, or explain how the model thinks.",
      action: "help" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [typingIdx, setTypingIdx] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, busy, typingIdx]);

  const send = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: message }]);
    setBusy(true);
    try {
      const s = useAppStore.getState();
      const res = await api.chat(message, {
        business_type: s.businessType,
        last_analysis: s.analysis,
      });
      setMsgs((m) => {
        const next = [...m, {
          role: "assistant" as const, text: res.reply, action: res.action, data: res.data,
          citations: res.citations, used_llm: res.used_llm, provider: res.provider,
        }];
        if (variant === "page") setTypingIdx(next.length - 1);
        return next;
      });
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "assistant", text: `⚠ ${e?.message || "Assistant error"}` }]);
    } finally {
      setBusy(false);
    }
  };

  const analyzeZone = async (z: { latitude: number; longitude: number; h3?: string }) => {
    const s = useAppStore.getState();
    const name = z.h3 ? `Zone ${z.h3.slice(-6)}` : undefined;
    if (variant === "page") navigate("/map");
    s.setPin({ lat: z.latitude, lng: z.longitude, name });
    s.setRightTab("analysis");
    s.setAnalyzing(true); s.setAnalysisError(null);
    try {
      const a = await api.analyze({ name: name ?? null, latitude: z.latitude, longitude: z.longitude,
        business_type: s.businessType, weights: s.weights });
      s.setAnalysis(a);
      flyToSite(z.latitude, z.longitude, 14);
    } catch (e: any) {
      s.setAnalysisError(e.message);
    } finally {
      s.setAnalyzing(false);
    }
  };

  const openOnMap = (lat: number, lng: number, name?: string) => {
    if (variant === "page") navigate("/map");
    useAppStore.getState().setPin({ lat, lng, name });
    setTimeout(() => flyToSite(lat, lng, 14), 50);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* messages */}
      <div ref={scrollRef} className={`min-h-0 flex-1 space-y-3 overflow-y-auto ${variant === "page" ? "pr-2" : "pr-1"}`}>
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={`${variant === "page" ? "max-w-[86%]" : "max-w-[92%]"} rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed ${
              m.role === "user"
                ? "rounded-br-md bg-accent-600 text-white shadow"
                : "rounded-bl-md border border-ink-600 bg-ink-800 text-slate-200"}`}>
              {m.role === "assistant" && (
                <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold text-accent-300">
                  <Bot size={11} /> GeoReady Assistant
                  {m.used_llm !== undefined && (
                    <span className={`ml-auto rounded px-1 py-0.5 text-[9px] ${
                      m.used_llm ? "bg-mint-500/15 text-mint-300" : "bg-ink-700 text-slate-400"}`}>
                      {m.used_llm ? `⚡ ${m.provider}` : "🛠 deterministic"}
                    </span>
                  )}
                </div>
              )}

              {m.role === "assistant" && i === typingIdx
                ? <TypeText text={m.text} onDone={() => setTypingIdx(null)} />
                : <div className="whitespace-pre-wrap">{m.text}</div>}

              {/* action payloads */}
              {i !== typingIdx && m.action === "recommend" && m.data?.zones?.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="flex flex-wrap gap-1">
                    {m.data.zones.map((z: any) => (
                      <span key={z.h3} className="flex items-center gap-1 rounded-md bg-ink-700 px-1.5 py-1 text-[10px]">
                        <span className="font-mono font-bold" style={{ color: z.color }}>{Math.round(z.overall)}</span>
                        zone {z.h3.slice(-6)}
                        <button title="Fly there" onClick={() => openOnMap(z.latitude, z.longitude)}
                          className="text-accent-300 hover:text-accent-400"><MapPin size={10} /></button>
                        <button title="Analyse this zone" onClick={() => analyzeZone(z)}
                          className="text-mint-300 hover:text-mint-400"><Target size={10} /></button>
                      </span>
                    ))}
                  </div>
                  {variant === "page" && (
                    <button className="btn-ghost text-[10px]" onClick={() => {
                      useAppStore.getState().setRecommendZones(m.data.zones);
                      navigate("/map");
                    }}>
                      <ArrowRight size={11} /> Open all zones on the map
                    </button>
                  )}
                </div>
              )}
              {i !== typingIdx && m.action === "analyze" && m.data?.analysis && (
                <button className="btn-ghost mt-2 text-[10px]" onClick={() => {
                  const s = useAppStore.getState();
                  const a = m.data.analysis;
                  s.setPin({ lat: a.latitude, lng: a.longitude, name: a.name });
                  s.setAnalysis(a);
                  s.setRightTab("analysis");
                  if (variant === "page") navigate("/map");
                  else flyToSite(a.latitude, a.longitude);
                }}>
                  <Target size={11} /> {variant === "page" ? "Open on map + analysis panel" : "Open in analysis panel"}
                </button>
              )}
              {i !== typingIdx && m.action === "compare" && m.data?.results && (
                <button className="btn-ghost mt-2 text-[10px]" onClick={() => {
                  const s = useAppStore.getState();
                  s.clearCompare();
                  m.data.results.forEach((r: any) => s.addToCompare(r));
                  navigate("/compare");
                }}>
                  <GitCompareArrows size={11} /> Open full comparison
                </button>
              )}

              {/* RAG sources with real document paths */}
              {i !== typingIdx && m.action === "knowledge" && (m.data?.sources?.length ?? 0) > 0 && (
                <div className="mt-2 space-y-1 border-t border-ink-700 pt-1.5">
                  <div className="text-[9px] font-bold uppercase tracking-wide text-slate-500">
                    Sources — semantic top-{m.data.sources.length} (vector similarity)
                  </div>
                  {m.data.sources.map((c: any, j: number) => (
                    <div key={j} className="flex items-center gap-1.5 text-[9.5px] text-slate-400">
                      <FileText size={9} className="shrink-0 text-accent-400" />
                      <span className="font-medium text-slate-300">{c.title}</span>
                      <span className="font-mono text-[8.5px] text-slate-600">{String(c.source).replace("rag/documents/", "")}</span>
                      <span className="ml-auto h-1 w-14 overflow-hidden rounded-full bg-ink-700">
                        <span className="block h-full rounded-full bg-accent-500" style={{ width: `${Math.round(c.score * 100)}%` }} />
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {i !== typingIdx && m.action !== "knowledge" && m.citations && m.citations.length > 0 && (
                <div className="mt-2 flex items-start gap-1 border-t border-ink-700 pt-1.5 text-[9.5px] text-slate-500">
                  <BookOpen size={10} className="mt-0.5 shrink-0" />
                  <span>{m.citations.slice(0, 3).join(" · ")}{m.citations.length > 3 ? ` +${m.citations.length - 3}` : ""}</span>
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <Loader2 size={12} className="animate-spin text-accent-400" /> querying the engine…
          </div>
        )}
      </div>

      {/* quick prompts */}
      {msgs.length < 3 && (
        <div className={`mt-2 flex flex-wrap gap-1.5 ${variant === "page" ? "justify-center" : ""}`}>
          {QUICK_PROMPTS.map((q) => (
            <button key={q} onClick={() => send(q)}
              className={`rounded-full border border-ink-600 bg-ink-800 text-slate-300 hover:border-accent-500 hover:text-accent-300
                ${variant === "page" ? "px-3.5 py-1.5 text-[11px]" : "px-2 py-1 text-[10px] text-slate-400"}`}>
              {q}
            </button>
          ))}
        </div>
      )}

      {/* input */}
      <div className={`mt-2 flex items-center gap-1.5 ${variant === "page" ? "mt-3" : ""}`}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about zones, sites, factors, the model, Rajkot…"
          className={`flex-1 rounded-xl border border-ink-600 bg-ink-800 px-3.5 text-[12px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent-500
            ${variant === "page" ? "py-3 shadow-inner" : "py-2"}`}
        />
        <button onClick={() => send()} disabled={busy || !input.trim()}
          className={`rounded-xl bg-accent-600 text-white hover:bg-accent-500 disabled:opacity-40 ${variant === "page" ? "p-3" : "p-2"}`}>
          <Send size={14} />
        </button>
      </div>
      <div className={`mt-1.5 flex items-center gap-1 text-[9.5px] text-slate-600 ${variant === "page" ? "justify-center" : ""}`}>
        <Sparkles size={10} /> Numbers from the engine · answers grounded via RAG top-k <Sparkles size={10} />
      </div>
    </div>
  );
}
