import { MapPin, Plus, Trash2 } from "lucide-react";
import { flyToSite } from "../../map/singleton";
import { api } from "../../services/api";
import { useAnalysis } from "../../services/useAnalysis";
import { useAppStore } from "../../store/useAppStore";

export default function CandidateSites() {
  const sites = useAppStore((s) => s.sites);
  const setSites = useAppStore((s) => s.setSites);
  const pin = useAppStore((s) => s.pin);
  const businessType = useAppStore((s) => s.businessType);
  const { run } = useAnalysis();

  const refresh = () => api.sites().then((d) => setSites(d.sites)).catch(() => {});

  const pick = (lat: number, lng: number, name: string) => {
    useAppStore.getState().setPin({ lat, lng, name });
    flyToSite(lat, lng);
    run(lat, lng, name);
  };

  const savePin = async () => {
    if (!pin) return;
    const name = prompt("Name this candidate site:", pin.name || "My site");
    if (!name) return;
    try {
      await api.createSite({ name, latitude: pin.lat, longitude: pin.lng, business_type: businessType });
      await refresh();
    } catch (e: any) { alert(e.message); }
  };

  const remove = async (id: string) => {
    try { await api.deleteSite(id); await refresh(); } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="glass rounded-xl p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="panel-title">Candidate sites</div>
        <button onClick={savePin} disabled={!pin} title="Save current pin as candidate site"
          className="flex items-center gap-1 rounded-md bg-ink-700 px-1.5 py-1 text-[10px] font-semibold text-slate-300 hover:bg-ink-600 disabled:opacity-40">
          <Plus size={11} /> pin
        </button>
      </div>
      <div className="max-h-56 space-y-1 overflow-y-auto pr-1">
        {sites.map((s) => (
          <div key={s.id}
            className="group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs hover:bg-ink-800">
            <button onClick={() => pick(s.latitude, s.longitude, s.name)}
              className="flex flex-1 items-center gap-2 text-left">
              <MapPin size={12} className={s.preset ? "text-amber-400" : "text-mint-400"} />
              <span className="flex-1 text-slate-200">{s.name}</span>
            </button>
            {!s.preset && (
              <button onClick={() => remove(s.id)}
                className="hidden text-slate-500 hover:text-danger-400 group-hover:block">
                <Trash2 size={12} />
              </button>
            )}
          </div>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-slate-500">
        Click anywhere on the map to drop a pin — or click a candidate marker.
      </p>
    </div>
  );
}
