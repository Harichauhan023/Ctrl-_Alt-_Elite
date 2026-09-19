import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Bot, GitCompareArrows, Loader2, MapPin, Send, Sparkles, Target } from "lucide-react";
import { flyToSite } from "../../map/singleton";
import { api } from "../../services/api";
import { useAppStore } from "../../store/useAppStore";
import type { ChatMsg } from "../../types";

const QUICK_PROMPTS = [
  "Recommend top 5 zones for EV charging",
  "Best areas for a warehouse, no competitors nearby",
  "How is Kalawad for an EV charger?",
  "Compare Old City vs Greenland for retail",
  "What does NOT_SUITABLE mean?",
  "Explain distance decay",
];

export default function ChatPanel() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([
    { role: "assistant", text: "👋 I'm the GeoReady Assistant. I drive the real scoring engine — ask me to recommend zones, analyse named sites, compare locations, or explain how the model thinks.", action: "help" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

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
      setMsgs((m) => [...m, {
        role: "assistant", text: res.reply, action: res.action, data: res.data,
        citations: res.citations, used_llm: res.used_llm, provider: res.provider,
      }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "assistant", text: `⚠ ${e?.message || "Assistant error"}` }]);
    } finally {
      setBusy(false);
    }
  };

  const analyzeZone = (z: { latitude: number; longitude: number; h3?: string }) => {
    const s = useAppStore.getState();
    s.setPin({ lat: z.latitude, lng: z.longitude, name: z.h3 ? `Zone ${z.h3.slice(-6)}` : undefined });
    s.setRightTab("analysis");
    flyToSite(z.latitude, z.longitude, 14);
    import("../../services/useAnalysis").then(() => {});
    // trigger run through the shared hook contract
    s.setAnalyzing(true); s.setAnalysisError(null);
    api.analyze({
      name: z.h3 ? `Zone ${z.h3.slice(-6)}` : null,
      latitude: z.latitude, longitude: z.longitude,
      business_type: s.businessType, weights: s.weights,
    }).then((a) => s.setAnalysis(a)).catch((e) => s.setAnalysisError(e.message))
      .finally(() => s.setAnalyzing(false));
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {/* messages */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={`max-w-[92%] rounded-xl px-3 py-2 text-[12px] leading-relaxed ${
              m.role === "user"
                ? "bg-accent-600 text-white"
                : "border border-ink-600 bg-ink-800 text-slate-200"}`}>
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
              <div className="whitespace-pre-wrap">{m.text}</div>

              {/* action payloads */}
              {m.action === "recommend" && m.data?.zones?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {m.data.zones.map((z: any) => (
                    <span key={z.h3} className="flex items-center gap-1 rounded-md bg-ink-700 px-1.5 py-1 text-[10px]">
                      <span className="font-mono font-bold" style={{ color: z.color }}>{Math.round(z.overall)}</span>
                      zone {z.h3.slice(-6)}
                      <button title="Fly there" onClick={() => flyToSite(z.latitude, z.longitude, 13.5)}
                        className="text-accent-300 hover:text-accent-400"><MapPin size={10} /></button>
                      <button title="Analyse this zone" onClick={() => analyzeZone(z)}
                        className="text-mint-300 hover:text-mint-400"><Target size={10} /></button>
                    </span>
                  ))}
                </div>
              )}
              {m.action === "analyze" && m.data?.analysis && (
                <button className="btn-ghost mt-2 text-[10px]" onClick={() => {
                  const s = useAppStore.getState();
                  const a = m.data.analysis;
                  s.setPin({ lat: a.latitude, lng: a.longitude, name: a.name });
                  s.setAnalysis(a);
                  s.setRightTab("analysis");
                  import("../../map/singleton").then(() => {});
                }}>
                  <Target size={11} /> Open in analysis panel
                </button>
              )}
              {m.action === "compare" && m.data?.results && (
                <button className="btn-ghost mt-2 text-[10px]" onClick={() => {
                  const s = useAppStore.getState();
                  s.clearCompare();
                  m.data.results.forEach((r: any) => s.addToCompare(r));
                  navigate("/compare");
                }}>
                  <GitCompareArrows size={11} /> Open full comparison
                </button>
              )}
              {m.citations && m.citations.length > 0 && (
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
        <div className="mt-2 flex flex-wrap gap-1">
          {QUICK_PROMPTS.map((q) => (
            <button key={q} onClick={() => send(q)}
              className="rounded-full border border-ink-600 bg-ink-800 px-2 py-1 text-[10px] text-slate-400 hover:border-accent-500 hover:text-accent-300">
              {q}
            </button>
          ))}
        </div>
      )}

      {/* input */}
      <div className="mt-2 flex items-center gap-1.5">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask about zones, sites, factors, Rajkot…"
          className="flex-1 rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-[12px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent-500"
        />
        <button onClick={() => send()} disabled={busy || !input.trim()}
          className="rounded-lg bg-accent-600 p-2 text-white hover:bg-accent-500 disabled:opacity-40">
          <Send size={14} />
        </button>
      </div>
      <div className="mt-1.5 flex items-center gap-1 text-[9.5px] text-slate-600">
        <Sparkles size={10} /> Numbers always come from the engine · citations from RAG (44 chunks, local MiniLM)
      </div>
    </div>
  );
}
