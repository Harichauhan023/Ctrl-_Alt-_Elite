import { Bot, Layers, PanelRightOpen, Shapes, X } from "lucide-react";
import { useAppStore } from "../../store/useAppStore";
import AnalysisPanel from "./AnalysisPanel";
import AreaPanel from "./AreaPanel";
import ChatBox from "../Assistant/ChatBox";

const TABS = [
  { key: "analysis" as const, label: "Analysis", icon: Layers },
  { key: "area" as const, label: "Area", icon: Shapes },
  { key: "assistant" as const, label: "Assistant", icon: Bot },
];

export default function RightDock() {
  const tab = useAppStore((s) => s.rightTab);
  const open = useAppStore((s) => s.rightDockOpen);
  const setOpen = useAppStore((s) => s.setRightDockOpen);
  const polygonResult = useAppStore((s) => s.polygonResult);
  const analysis = useAppStore((s) => s.analysis);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        title="Open results panel"
        className="glass absolute right-3 top-14 z-10 flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-[11px] font-semibold text-accent-300 hover:bg-ink-700">
        <PanelRightOpen size={13} /> Panel
        {(analysis || polygonResult) && <span className="h-1.5 w-1.5 rounded-full bg-accent-400" />}
      </button>
    );
  }

  return (
    <div className="glass absolute bottom-3 right-3 top-14 z-10 flex w-[392px] flex-col overflow-hidden rounded-xl">
      <div className="flex shrink-0 items-stretch border-b border-ink-700">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => useAppStore.getState().setRightTab(key)}
            className={`flex flex-1 items-center justify-center gap-1.5 px-2 py-2.5 text-[11px] font-semibold transition-colors ${
              tab === key ? "bg-ink-700/70 text-accent-300" : "text-slate-500 hover:bg-ink-800 hover:text-slate-300"}`}>
            <Icon size={13} /> {label}
            {key === "area" && polygonResult && <span className="h-1.5 w-1.5 rounded-full bg-mint-400" />}
            {key === "analysis" && analysis && <span className="h-1.5 w-1.5 rounded-full bg-accent-400" />}
          </button>
        ))}
        {/* always-closable (per requirement: every panel has an X) */}
        <button onClick={() => setOpen(false)} title="Close panel"
          className="flex w-8 items-center justify-center text-slate-500 hover:bg-ink-800 hover:text-slate-200">
          <X size={13} />
        </button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-3.5">
        {tab === "analysis" && <AnalysisPanel docked />}
        {tab === "area" && <AreaPanel />}
        {tab === "assistant" && <ChatBox variant="dock" />}
      </div>
    </div>
  );
}
