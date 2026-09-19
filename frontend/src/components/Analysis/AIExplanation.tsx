import { AlertTriangle, Bot, CheckCircle2, Database, FileText, Sparkles, Zap } from "lucide-react";
import type { ExplainResponse } from "../../types";

/** Renders the explainable-AI block (works for both Gemini and deterministic fallback). */
export default function AIExplanation({ data }: { data: ExplainResponse }) {
  const { explanation: ex, meta } = data;
  return (
    <div className="rounded-xl border border-accent-600/25 bg-accent-600/5 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Sparkles size={13} className="text-accent-300" />
        <span className="text-xs font-bold text-accent-300">AI Explanation</span>
        <span className={`ml-auto flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold ${
          meta.used_llm ? "bg-mint-500/15 text-mint-300" : "bg-ink-700 text-slate-300"}`}>
          <Bot size={11} />
          {meta.used_llm ? `${meta.provider} · ${meta.model}` : "deterministic explainer"}
        </span>
        {meta.cached && <span className="rounded bg-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400">cached</span>}
      </div>

      <p className="text-[12px] leading-relaxed text-slate-200">{ex.summary}</p>

      {!!ex.strengths?.length && (
        <div className="mt-2 space-y-1">
          {ex.strengths.map((s, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px] text-mint-300">
              <CheckCircle2 size={12} className="mt-0.5 shrink-0" /> <span>{s}</span>
            </div>
          ))}
        </div>
      )}
      {!!ex.risks?.length && (
        <div className="mt-1.5 space-y-1">
          {ex.risks.map((s, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-300">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" /> <span>{s}</span>
            </div>
          ))}
        </div>
      )}
      {ex.key_reason && (
        <div className="mt-2 rounded-lg bg-ink-800/80 p-2 text-[11px] leading-snug text-slate-300">
          <Zap size={11} className="mr-1 inline text-amber-400" />
          <span className="font-semibold text-slate-200">Key reason: </span>{ex.key_reason}
        </div>
      )}
      {ex.answer && (
        <div className="mt-2 rounded-lg border border-ink-600 p-2 text-[11px] text-slate-300">
          <span className="font-semibold text-accent-300">Answer: </span>{ex.answer}
        </div>
      )}

      {/* RAG sources — REAL documents with file paths and similarity scores */}
      {(meta.sources?.length ?? 0) > 0 && (
        <div className="mt-2 rounded-lg border border-ink-700 bg-ink-900/60 p-2">
          <div className="mb-1 flex items-center gap-1 text-[9px] font-bold uppercase tracking-wide text-slate-500">
            <Database size={9} /> RAG sources · {meta.rag_mode} · top-{meta.sources!.length}
          </div>
          <div className="space-y-1">
            {meta.sources!.map((c, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[9.5px]">
                <FileText size={9} className="shrink-0 text-accent-400" />
                <span className="max-w-[46%] truncate text-slate-300" title={c.title}>{c.title}</span>
                <span className="truncate font-mono text-[8.5px] text-slate-600" title={c.source}>
                  {c.source.replace("rag/documents/", "")}
                </span>
                <span className="ml-auto h-1 w-12 shrink-0 overflow-hidden rounded-full bg-ink-700">
                  <span className="block h-full rounded-full bg-accent-500"
                    style={{ width: `${Math.round(Math.min(1, Math.max(0, c.score)) * 100)}%` }} />
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* pipeline trace — how this result was built */}
      {meta.pipeline && (
        <div className="mt-2 flex flex-wrap items-center gap-1 text-[9px] text-slate-500">
          <span className="font-bold uppercase tracking-wide">Pipeline:</span>
          <Chip ok label={`features ${meta.pipeline.features}`} />
          <Chip ok label={meta.pipeline.ml ? "ML ✓" : "ML —"} />
          <Chip ok label={`RAG ${meta.pipeline.rag_chunks} chunks`} />
          <Chip ok label={meta.used_llm ? String(meta.provider) : "deterministic"} />
        </div>
      )}
      {!meta.sources?.length && (
        <div className="mt-2 flex items-start gap-1.5 text-[10px] text-slate-500">
          <Database size={11} className="mt-0.5 shrink-0" />
          <span>RAG ({meta.rag_mode}): {(meta.rag_sources || []).slice(0, 3).join(" · ")}</span>
        </div>
      )}
    </div>
  );
}

function Chip({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono ${ok ? "bg-mint-500/10 text-mint-300" : "bg-ink-700 text-slate-500"}`}>
      {label}
    </span>
  );
}
