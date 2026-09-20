import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import maplibregl from "maplibre-gl";
import { Maximize2 } from "lucide-react";
import { BASEMAP_FALLBACK, STYLE_DARK, styleFor } from "../../map/basemaps";
import { api } from "../../services/api";
import { useAppStore } from "../../store/useAppStore";

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

/**
 * Compact live preview map for the chat landing page.
 * Real basemap tiles + readiness heatmap + candidate sites — same pipe as the
 * big map. If a basemap's tiles are unreachable it auto-walks the fallback chain.
 */
export default function MiniMap({ className = "" }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const dataCache = useRef<{ hs?: any; sites?: any }>({});
  const curStyle = useRef<string>("");
  const failedStyles = useRef<Set<string>>(new Set());
  const fnBound = useRef(false);
  const [dead, setDead] = useState(false);
  const navigate = useNavigate();

  const basemap = useAppStore((s) => s.basemap);
  const businessType = useAppStore((s) => s.businessType);

  const installLayers = (map: maplibregl.Map) => {
    if (map.getSource("mm-sites")) return;            // idempotent
    const d = dataCache.current;
    map.addSource("mm-hs", { type: "geojson", data: d.hs ?? EMPTY_FC });
    map.addSource("mm-sites", { type: "geojson", data: d.sites ?? EMPTY_FC });
    map.addLayer({ id: "mm-hs-fill", type: "fill", source: "mm-hs",
      paint: { "fill-color": ["get", "color"], "fill-opacity": 0.5 } });
    map.addLayer({ id: "mm-sites-circle", type: "circle", source: "mm-sites", paint: {
      "circle-radius": 4.5, "circle-color": "#fbbf24",
      "circle-stroke-color": "#0a0f1c", "circle-stroke-width": 1.4 } });
  };

  const bindClick = (map: maplibregl.Map) => {
    if (fnBound.current) return;
    fnBound.current = true;
    map.on("click", (e) => {
      if (!map.getLayer("mm-sites-circle")) return;
      const f = map.queryRenderedFeatures(e.point, { layers: ["mm-sites-circle"] })[0];
      if (!f) return;
      const p: any = f.properties;
      const g: any = f.geometry;
      useAppStore.getState().setPin({ lat: g.coordinates[1], lng: g.coordinates[0], name: p.name });
      navigate("/map");
    });
  };

  const applyMini = (map: maplibregl.Map, id: string) => {
    curStyle.current = id;
    map.setStyle(styleFor(id));
    map.once("style.load", () => {
      if (!mapRef.current) return;
      try {
        installLayers(map);
        bindClick(map);
      } catch { /* retry at next event */ }
    });
  };

  useEffect(() => {
    if (!containerRef.current) return;
    let deadLocal = false;
    (async () => {
      let styleId = basemap;
      if (basemap === "dark") {
        try {
          const r = await fetch(STYLE_DARK, { signal: AbortSignal.timeout(4500) });
          if (!r.ok) styleId = "streets";
        } catch { styleId = "streets"; }
      }
      if (deadLocal || !containerRef.current) return;
      let map: maplibregl.Map;
      try {
        map = new maplibregl.Map({
          container: containerRef.current, style: styleFor(styleId),
          center: [70.8022, 22.3039], zoom: 10.9, minZoom: 9, maxZoom: 15,
          attributionControl: { compact: true },
        } as any);
      } catch {
        setDead(true);
        return;
      }
      mapRef.current = map;
      curStyle.current = styleId;

      // app data → overlay polygon + pins
      Promise.allSettled([
        api.hotspots(useAppStore.getState().businessType, null),
        api.sites(),
      ]).then(([hs, sites]) => {
        if (hs.status === "fulfilled") dataCache.current.hs = hs.value.geojson;
        if (sites.status === "fulfilled") {
          dataCache.current.sites = {
            type: "FeatureCollection",
            features: sites.value.sites.map((s: any) => ({
              type: "Feature", properties: { id: s.id, name: s.name },
              geometry: { type: "Point", coordinates: [s.longitude, s.latitude] },
            })),
          };
        }
        if (mapRef.current) {
          try {
            if (map.getSource("mm-sites")) {
              // layers already installed EMPTY → push the data now
              (map.getSource("mm-hs") as maplibregl.GeoJSONSource)?.setData(dataCache.current.hs ?? EMPTY_FC);
              (map.getSource("mm-sites") as maplibregl.GeoJSONSource)?.setData(dataCache.current.sites ?? EMPTY_FC);
            } else {
              installLayers(map);
            }
            bindClick(map);
          } catch { /* wait for style.load */ }
        }
      });

      map.on("style.load", () => { try { installLayers(map); bindClick(map); } catch { /* soon */ } });
      map.on("load", () => { try { installLayers(map); bindClick(map); } catch { /* soon */ } });
      setTimeout(() => {
        if (mapRef.current) { try { installLayers(map); bindClick(map); } catch { /* ok */ } }
      }, 5000);

      // 🛡️ auto-fallback when the chosen basemap's tiles never arrive
      map.on("error", (e: any) => {
        const cur = curStyle.current;
        if (!cur || failedStyles.current.has(cur)) return;
        const msg = String(e?.error?.message ?? "");
        if (e?.sourceId && ["mm-hs", "mm-sites"].includes(e.sourceId)) return;
        const hosts: Record<string, string> = {
          dark: "openfreemap", streets: "openstreetmap.org", satellite: "arcgisonline.com",
        };
        const host = hosts[cur];
        if (!host || !msg.toLowerCase().includes(host) && !/style|tile|glyph/i.test(msg)) return;
        failedStyles.current.add(cur);
        const next = BASEMAP_FALLBACK[cur] ?? "offline";
        console.warn(`⚠ mini-map: "${cur}" unreachable → "${next}"`);
        applyMini(map, next);
        useAppStore.setState({ basemap: (next === "offline" ? "dark" : next) as any });
      });
    })();
    return () => {
      deadLocal = true;
      mapRef.current?.remove();
      mapRef.current = null;
      fnBound.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || curStyle.current === basemap) return;
    applyMini(map, basemap);
  }, [basemap]);

  return (
    <div className={`relative overflow-hidden rounded-2xl border border-ink-700 ${className}`}>
      {dead ? (
        <div className="flex h-full items-center justify-center bg-ink-900 text-[11px] text-slate-500">
          Map preview unavailable — <button className="ml-1 text-accent-300 underline" onClick={() => navigate("/map")}>open the full map</button>
        </div>
      ) : (
        <>
          <div ref={containerRef} className="h-full w-full" />
          {/* overlays */}
          <div className="pointer-events-none absolute left-2.5 top-2 flex flex-col gap-1">
            <span className="glass w-fit rounded-md px-1.5 py-0.5 text-[9px] font-semibold text-accent-300">
              ● live mini-map · Rajkot
            </span>
            <span className="glass w-fit rounded-md px-1.5 py-0.5 text-[8.5px] text-slate-400">
              colors = AI readiness zones · 🟡 = candidate sites
            </span>
          </div>
          <button
            onClick={() => navigate("/map")}
            className="absolute right-2.5 top-2 flex items-center gap-1 rounded-lg bg-accent-600/90 px-2.5 py-1.5 text-[10px] font-bold text-white shadow-lg backdrop-blur transition hover:bg-accent-500"
          >
            <Maximize2 size={11} /> Full map
          </button>
          <div className="pointer-events-none absolute bottom-1.5 left-2.5 rounded bg-ink-950/70 px-1.5 py-0.5 text-[8px] text-slate-500 backdrop-blur">
            {businessType.replaceAll("_", " ").toLowerCase()} lens · click a pin or expand
          </div>
        </>
      )}
    </div>
  );
}
