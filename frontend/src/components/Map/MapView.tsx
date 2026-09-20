import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { Check, Pencil, X } from "lucide-react";
import { api } from "../../services/api";
import { useAnalysis } from "../../services/useAnalysis";
import { BASEMAP_FALLBACK, BASEMAP_LABEL, BASEMAP_MAP, OFFLINE_STYLE, STYLE_DARK, isRaster, styleFor } from "../../map/basemaps";
import { mapSingleton } from "../../map/singleton";
import { useAppStore } from "../../store/useAppStore";

const DATA_LAYERS = ["population", "roads", "competitors", "landuse", "risk", "hospitals", "schools", "fuel"];
const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

const VIS_MAP: Record<string, { ids: string[]; paints?: [string, string[]][] }> = {
  population:  { ids: ["population-fill"], paints: [["population-fill", ["fill-opacity"]]] },
  roads:       { ids: ["roads-line"], paints: [["roads-line", ["line-opacity"]]] },
  competitors: { ids: ["competitors-circle"], paints: [["competitors-circle", ["circle-opacity", "circle-stroke-opacity"]]] },
  landuse:     { ids: ["landuse-fill"], paints: [["landuse-fill", ["fill-opacity"]]] },
  risk:        { ids: ["risk-fill"], paints: [["risk-fill", ["fill-opacity"]]] },
  hospitals:   { ids: ["hospitals-circle"] },
  schools:     { ids: ["schools-circle"] },
  fuel:        { ids: ["fuel-circle"] },
};

function src(map: maplibregl.Map, id: string) {
  return map.getSource(id) as maplibregl.GeoJSONSource | undefined;
}

export default function MapView() {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [tiles, setTiles] = useState<"loading" | "online" | "offline">("loading");
  const [note, setNote] = useState<string | null>(null);
  const [drawing, setDrawing] = useState(0); // vertex count trigger
  const [styleKey, setStyleKey] = useState(0);
  const drawPts = useRef<number[][]>([]);
  const layerDataCache = useRef<Record<string, GeoJSON.FeatureCollection>>({});
  const handlersBound = useRef(false);
  const failedStyles = useRef<Set<string>>(new Set());
  const { run } = useAnalysis();

  const layerState = useAppStore((s) => s.layerState);
  const heatmapOn = useAppStore((s) => s.heatmapOn);
  const businessType = useAppStore((s) => s.businessType);
  const weights = useAppStore((s) => s.weights);
  const sites = useAppStore((s) => s.sites);
  const pin = useAppStore((s) => s.pin);
  const catchment = useAppStore((s) => s.catchment);
  const catchmentOn = useAppStore((s) => s.catchmentOn);
  const drawMode = useAppStore((s) => s.drawMode);
  const polygonCoords = useAppStore((s) => s.polygonCoords);
  const recommendZones = useAppStore((s) => s.recommendZones);
  const ghosts = useAppStore((s) => s.ghostCompetitors);
  const basemap = useAppStore((s) => s.basemap);

  const updateDraft = useCallback(() => {
    const map = mapSingleton.map;
    if (!map) return;
    const pts = drawPts.current;
    const line = pts.length >= 2 ? [[...pts, pts[0]]] : [];
    src(map, "draw")?.setData({
      type: "FeatureCollection",
      features: [
        ...(line.length ? [{ type: "Feature" as const, properties: {},
          geometry: { type: "LineString" as const, coordinates: line[0] } }] : []),
        ...pts.map((p) => ({ type: "Feature" as const, properties: {},
          geometry: { type: "Point" as const, coordinates: p } })),
      ],
    });
  }, []);

  const finishPolygon = useCallback(async () => {
    const pts = drawPts.current.filter((p, i) =>
      i === 0 || p[0] !== drawPts.current[i - 1][0] || p[1] !== drawPts.current[i - 1][1]);
    if (pts.length < 3) return;
    const s = useAppStore.getState();
    if (s.drawMode !== "polygon") return;
    s.setDrawMode(false);
    drawPts.current = [];
    updateDraft();
    try {
      const result = await api.polygonAnalyze({
        polygon: pts, business_type: s.businessType, weights: s.weights,
      });
      s.setPolygon(pts, result);
      s.setRightTab("area");
    } catch (e: any) {
      alert(e.message || "Area analysis failed");
    }
  }, [updateDraft]);

  const installDataLayers = useCallback((map: maplibregl.Map, withText: boolean) => {
    const data = layerDataCache.current;
    for (const n of DATA_LAYERS) map.addSource(n, { type: "geojson", data: data[n] ?? EMPTY_FC });
    for (const n of ["hotspots", "rings", "sites", "pin", "draw", "area", "ghosts", "recommend"])
      map.addSource(n, { type: "geojson", data: EMPTY_FC });

    map.addLayer({ id: "landuse-fill", type: "fill", source: "landuse", paint: {
      "fill-color": ["match", ["get", "category"],
        "commercial", "#d97706", "mixed_use", "#8b5cf6", "industrial", "#57534e",
        "residential", "#0e7490", "agricultural", "#4d7c0f", "protected", "#b91c1c", "#334155"],
      "fill-opacity": 0.45 } });
    map.addLayer({ id: "risk-fill", type: "fill", source: "risk", paint: {
      "fill-color": ["match", ["get", "risk_level"], "critical", "#7f1d1d", "high", "#ea580c", "#f59e0b"],
      "fill-opacity": 0.5 } });
    map.addLayer({ id: "risk-line", type: "line", source: "risk", paint: {
      "line-color": ["match", ["get", "risk_level"], "critical", "#ef4444", "high", "#fb923c", "#fbbf24"],
      "line-width": 1.2 } });
    map.addLayer({ id: "population-fill", type: "fill", source: "population", paint: {
      "fill-color": ["interpolate", ["linear"], ["get", "density"],
        0, "rgba(2,132,199,0.02)", 5000, "rgba(2,132,199,0.22)",
        13000, "rgba(56,189,248,0.5)", 24000, "rgba(125,211,252,0.85)"],
      "fill-opacity": 0.55 } });
    map.addLayer({ id: "heatmap-fill", type: "fill", source: "hotspots", layout: { visibility: "none" },
      paint: { "fill-color": ["get", "color"], "fill-opacity": 0.52 } });
    map.addLayer({ id: "heatmap-line", type: "line", source: "hotspots", layout: { visibility: "none" },
      paint: { "line-color": "#070b14", "line-width": 0.5, "line-opacity": 0.5 } });
    map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: {
      "line-color": isRaster((map as any)._georeadyStyleId) ? "#b45309"
        : ["case", ["==", ["get", "major"], true], "#e2e8f0", "#64748b"],
      "line-width": ["interpolate", ["linear"], ["zoom"],
        10, ["case", ["==", ["get", "major"], true], 1.6, 0.7],
        15, ["case", ["==", ["get", "major"], true], 4, 1.6]],
      "line-opacity": 0.9 } });
    map.addLayer({ id: "rings-fill", type: "fill", source: "rings", paint: {
      "fill-color": ["match", ["get", "minutes"], 10, "#34d399", 20, "#38bdf8", "#a78bfa"],
      "fill-opacity": 0.06 } });
    map.addLayer({ id: "rings-line", type: "line", source: "rings", paint: {
      "line-color": ["match", ["get", "minutes"], 10, "#34d399", 20, "#38bdf8", "#a78bfa"],
      "line-width": 2, "line-dasharray": [2, 1.6] } });
    const dot = (id: string, source: string, color: string, r: number) =>
      map.addLayer({ id, type: "circle", source, paint: {
        "circle-radius": r, "circle-color": color, "circle-stroke-color": "#0a0f1c", "circle-stroke-width": 1.4 } });
    dot("fuel-circle", "fuel", "#94a3b8", 4);
    dot("schools-circle", "schools", "#c084fc", 4);
    dot("hospitals-circle", "hospitals", "#2dd4bf", 4.5);
    dot("competitors-circle", "competitors", "#ef4444", 5.5);
    map.addLayer({ id: "area-fill", type: "fill", source: "area", paint: {
      "fill-color": "#2dd4bf", "fill-opacity": 0.1 } });
    map.addLayer({ id: "area-line", type: "line", source: "area", paint: {
      "line-color": "#2dd4bf", "line-width": 2, "line-dasharray": [3, 2] } });
    map.addLayer({ id: "draw-line", type: "line", source: "draw", filter: ["==", ["geometry-type"], "LineString"],
      paint: { "line-color": "#2dd4bf", "line-width": 2, "line-dasharray": [1.5, 1.5] } });
    map.addLayer({ id: "draw-pts", type: "circle", source: "draw", filter: ["==", ["geometry-type"], "Point"],
      paint: { "circle-radius": 4.5, "circle-color": "#2dd4bf", "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 } });
    map.addLayer({ id: "ghosts-circle", type: "circle", source: "ghosts", paint: {
      "circle-radius": 6.5, "circle-color": "#fb923c", "circle-opacity": 0.85,
      "circle-stroke-color": "#7c2d12", "circle-stroke-width": 2 } });
    map.addLayer({ id: "recommend-circle", type: "circle", source: "recommend", paint: {
      "circle-radius": 11, "circle-color": "#0a0f1c", "circle-stroke-color": "#34d399", "circle-stroke-width": 2.5 } });
    if (withText) {
      map.addLayer({ id: "recommend-label", type: "symbol", source: "recommend", layout: {
        "text-field": ["get", "rank"], "text-font": ["Noto Sans Bold"], "text-size": 11 },
        paint: { "text-color": "#6ee7b7" } });
    }
    map.addLayer({ id: "sites-circle", type: "circle", source: "sites", paint: {
      "circle-radius": ["case", ["==", ["get", "preset"], true], 7.5, 7],
      "circle-color": ["case", ["==", ["get", "preset"], true], "#fbbf24", "#34d399"],
      "circle-stroke-color": "#0a0f1c", "circle-stroke-width": 2 } });
    if (withText) {
      map.addLayer({ id: "sites-label", type: "symbol", source: "sites", layout: {
        "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"],
        "text-size": 11, "text-offset": [0, 1.15], "text-anchor": "top", "text-optional": true },
        paint: { "text-color": "#fde68a", "text-halo-color": "#070b14", "text-halo-width": 1.4 } });
    }
    map.addLayer({ id: "pin-outer", type: "circle", source: "pin", paint: {
      "circle-radius": 12, "circle-color": "rgba(56,189,248,0.25)" } });
    map.addLayer({ id: "pin-inner", type: "circle", source: "pin", paint: {
      "circle-radius": 6, "circle-color": "#38bdf8", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
  }, []);

  const ensureDataLayers = useCallback((map: maplibregl.Map) => {
    if (map.getSource("population")) return;         // already installed
    if (!map.isStyleLoaded() && !map.getLayer("osm-tiles") && !map.getLayer("esri-tiles")) {
      // style not committed yet — style.load will call us again
      return;
    }
    try {
      installDataLayers(map, (map as any)._georeadyStyleId !== "offline");
      setStyleKey((k) => k + 1);
    } catch (err) {
      console.warn("data layer install deferred:", err);
    }
  }, [installDataLayers]);

  /** Swap basemap style; re-install data once committed. */
  const applyStyle = useCallback((id: string, why?: string) => {
    const map = mapSingleton.map;
    if (!map) return;
    (map as any)._georeadyStyleId = id;
    try {
      map.setStyle(styleFor(id));
    } catch (err) {
      console.warn("setStyle failed", err);
    }
    if (why) setNote(why);
    map.once("style.load", () => {
      if (!mapSingleton.map) return;
      ensureDataLayers(map);
      setTiles(id === "offline" ? "offline" : "online");
    });
  }, [ensureDataLayers]);

  /** One-time binding of interaction handlers (works even before data layers exist). */
  const bindHandlers = useCallback((map: maplibregl.Map) => {
    if (handlersBound.current) return;
    handlersBound.current = true;
    const popup = new maplibregl.Popup({ closeButton: true, maxWidth: "320px" });

    map.on("click", (e) => {
      const st = useAppStore.getState();
      if (st.drawMode === "polygon") {
        drawPts.current = [...drawPts.current, [e.lngLat.lng, e.lngLat.lat]];
        setDrawing(drawPts.current.length);
        updateDraft();
        return;
      }
      if (st.drawMode === "ghost") {
        st.setDrawMode(false);
        st.addGhost({ lat: e.lngLat.lat, lng: e.lngLat.lng });
        const p = st.pin;
        if (p) run(p.lat, p.lng, p.name);
        return;
      }
      if (!map.getLayer("recommend-circle")) return;
      const rf = map.queryRenderedFeatures(e.point, { layers: ["recommend-circle"] });
      if (rf.length) {
        const p = rf[0].properties as any;
        const g = (rf[0].geometry as any).coordinates;
        st.setPin({ lat: g[1], lng: g[0], name: p.name });
        run(g[1], g[0], p.name);
        st.setRightTab("analysis");
        return;
      }
      if (map.getLayoutProperty("heatmap-fill", "visibility") === "visible") {
        const hs = map.queryRenderedFeatures(e.point, { layers: ["heatmap-fill"] });
        if (hs.length) {
          const p = hs[0].properties as any;
          popup.remove();
          const chip = (label: string, v: string) =>
            `<tr><td style="color:#94a3b8;padding-right:10px">${label}</td><td style="text-align:right;font-weight:600">${v}</td></tr>`;
          popup.setLngLat(e.lngLat).setHTML(
            `<div style="font-family:Inter"><div style="font-weight:700;font-size:13px;margin-bottom:6px">
             Zone readiness: <span style="color:${p.color}">${p.overall}</span>
             <span style="color:#94a3b8;font-weight:500">(${p.band})</span></div>
             <table style="font-size:11px">${chip("Population", p.population)}${chip("Accessibility", p.accessibility)}
             ${chip("Competition", p.competition)}${chip("Land use", `${p.land_use} · ${p.land_category}`)}
             ${chip("Environment", `${p.environment} · ${p.risk_level}`)}</table>
             ${p.constrained ? '<div style="margin-top:6px;color:#f87171;font-size:11px;font-weight:600">⚠ Hard constraint zone</div>' : ""}
             </div>`).addTo(map);
          return;
        }
      }
      const sf = map.queryRenderedFeatures(e.point, { layers: ["sites-circle"] });
      if (sf.length) {
        const p = sf[0].properties as any;
        st.setPin({ lat: p.latitude, lng: p.longitude, name: p.name });
        run(p.latitude, p.longitude, p.name);
        return;
      }
      const cf = map.queryRenderedFeatures(e.point, { layers: ["competitors-circle"] });
      if (cf.length) {
        const p = cf[0].properties as any;
        popup.setLngLat(e.lngLat).setHTML(
          `<div style="font-weight:700;font-size:12px">🔌 ${p.name}</div>
           <div style="font-size:11px;color:#94a3b8">${p.category} · source: ${p.source}</div>`).addTo(map);
        return;
      }
      popup.remove();
      st.setPin({ lat: e.lngLat.lat, lng: e.lngLat.lng });
      run(e.lngLat.lat, e.lngLat.lng);
    });
    for (const l of ["sites-circle", "competitors-circle", "heatmap-fill", "recommend-circle"]) {
      map.on("mouseenter", l, () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", l, () => (map.getCanvas().style.cursor = ""));
    }
  }, [run, updateDraft]);

  useEffect(() => {
    let dead = false;
    let fallbackTimer: ReturnType<typeof setTimeout> | undefined;

    (async () => {
      const wanted = useAppStore.getState().basemap;   // may be a stored bad choice — fallback fixes it live
      let styleId = wanted;
      if (wanted === "dark") {
        try {
          const r = await fetch(STYLE_DARK, { signal: AbortSignal.timeout(5000) });
          if (!r.ok) styleId = "streets";
        } catch { styleId = "streets"; }
      }
      if (dead) return;

      const map = new maplibregl.Map({
        container: ref.current!, style: styleFor(styleId),
        center: [70.8022, 22.3039], zoom: 11.6, minZoom: 9, maxZoom: 17,
        attributionControl: { compact: true },
      });
      map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
      map.addControl(new maplibregl.ScaleControl(), "bottom-left");
      (map as any)._georeadyStyleId = styleId;
      mapSingleton.map = map;
      setTiles("online");

      // prefetch app data so style commits don't wait on network
      Promise.allSettled(DATA_LAYERS.map(async (n) => {
        layerDataCache.current[n] = await api.layerData(n);
      })).then(() => {
        if (dead || !mapSingleton.map) return;
        // layers may already be installed EMPTY (style beat the fetch) → push now
        for (const n of DATA_LAYERS) {
          const data = layerDataCache.current[n];
          if (data) src(map, n)?.setData(data);
        }
        ensureDataLayers(map);
        setStyleKey((k) => k + 1);
      });

      map.on("style.load", () => ensureDataLayers(map));
      map.on("load", () => {
        ensureDataLayers(map);
        bindHandlers(map);
        setReady(true);
      });
      // belt & suspenders: if 'load' never fires (dead tile CDN), still arm the app
      fallbackTimer = setTimeout(() => {
        if (dead || !mapSingleton.map) return;
        ensureDataLayers(map);
        bindHandlers(map);
        setReady(true);
      }, 6000);

      // 🛡️ tiles unreachable? auto-walk the fallback chain so a REAL map always renders
      map.on("error", (e: any) => {
        const cur = (map as any)._georeadyStyleId as string;
        if (!cur || failedStyles.current.has(cur)) return;
        const msg = String(e?.error?.message ?? "");
        // ignore our own geojson errors; only care about basemap resources
        if (e?.sourceId && DATA_LAYERS.includes(e.sourceId)) return;
        const styleHosts: Record<string, string> = {
          dark: "openfreemap", streets: "openstreetmap.org", satellite: "arcgisonline.com",
        };
        const host = styleHosts[cur];
        if (!host || !msg.toLowerCase().includes(host) && !msg.toLowerCase().includes("style") && !msg.toLowerCase().includes("tile")) return;
        failedStyles.current.add(cur);
        const next = BASEMAP_FALLBACK[cur] ?? "offline";
        console.warn(`⚠ basemap "${cur}" unreachable (${msg.slice(0, 90)}) → falling back to "${next}"`);
        applyStyle(next, `${BASEMAP_LABEL[cur] ?? cur} unreachable — switched to ${BASEMAP_LABEL[next] ?? next}`);
        useAppStore.setState({ basemap: (next === "offline" ? "dark" : next) as any });
      });
    })();

    return () => {
      dead = true;
      if (fallbackTimer) clearTimeout(fallbackTimer);
      handlersBound.current = false;
      mapSingleton.map?.remove();
      mapSingleton.map = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    if ((map as any)._georeadyStyleId === basemap) return;
    ensureDataLayers(map);
    setNote(null);
    applyStyle(basemap);
  }, [basemap, ready, applyStyle, ensureDataLayers]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    if (drawMode) {
      map.getCanvas().style.cursor = "crosshair";
      const key = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          useAppStore.getState().setDrawMode(false);
          drawPts.current = []; setDrawing(0); updateDraft();
        }
        if (e.key === "Enter" && useAppStore.getState().drawMode === "polygon") finishPolygon();
      };
      let dbl: ((e: maplibregl.MapMouseEvent) => void) | undefined;
      if (drawMode === "polygon") {
        map.doubleClickZoom.disable();
        drawPts.current = [];
        setDrawing(0);
        updateDraft();
        dbl = (e: maplibregl.MapMouseEvent) => { e.preventDefault(); finishPolygon(); };
        map.on("dblclick", dbl);
      }
      window.addEventListener("keydown", key);
      return () => {
        if (dbl) map.off("dblclick", dbl);
        window.removeEventListener("keydown", key);
        map.doubleClickZoom.enable();
        map.getCanvas().style.cursor = "";
      };
    }
  }, [drawMode, ready, finishPolygon, updateDraft]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    for (const [name, s] of Object.entries(layerState)) {
      const conf = VIS_MAP[name];
      if (!conf) continue;
      for (const id of conf.ids) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", s.visible ? "visible" : "none");
      }
      if (s.visible && conf.paints) {
        for (const [id, paints] of conf.paints) {
          for (const p of paints) if (map.getLayer(id)) map.setPaintProperty(id, p, s.opacity);
        }
      }
    }
  }, [layerState, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    const vis = heatmapOn ? "visible" : "none";
    for (const id of ["heatmap-fill", "heatmap-line"]) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
    }
    if (!heatmapOn) return;
    const t = setTimeout(async () => {
      const w = useAppStore.getState().weights;
      const frac = { population: w.population / 100, accessibility: w.accessibility / 100,
        competition: w.competition / 100, land_use: w.land_use / 100, environment: w.environment / 100 };
      try {
        const data = await api.hotspots(useAppStore.getState().businessType, frac);
        src(map, "hotspots")?.setData(data.geojson);
      } catch { /* keep old */ }
    }, 300);
    return () => clearTimeout(t);
  }, [heatmapOn, businessType, weights, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    src(map, "sites")?.setData({
      type: "FeatureCollection",
      features: sites.map((s) => ({ type: "Feature",
        properties: { id: s.id, name: s.name, preset: s.preset, latitude: s.latitude, longitude: s.longitude },
        geometry: { type: "Point", coordinates: [s.longitude, s.latitude] } })),
    });
  }, [sites, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    src(map, "pin")?.setData(pin ? { type: "FeatureCollection",
      features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [pin.lng, pin.lat] } }],
    } : EMPTY_FC);
  }, [pin, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    const show = catchmentOn && catchment;
    for (const id of ["rings-fill", "rings-line"]) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", show ? "visible" : "none");
    }
    src(map, "rings")?.setData(show ? catchment.rings_geojson : EMPTY_FC);
  }, [catchment, catchmentOn, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    src(map, "ghosts")?.setData({
      type: "FeatureCollection",
      features: ghosts.map((g) => ({ type: "Feature", properties: {},
        geometry: { type: "Point", coordinates: [g.lng, g.lat] } })),
    });
  }, [ghosts, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    src(map, "recommend")?.setData({
      type: "FeatureCollection",
      features: recommendZones.map((z, i) => ({ type: "Feature",
        properties: { rank: `#${i + 1}`, name: `Zone ${z.h3.slice(-6)}` },
        geometry: { type: "Point", coordinates: [z.longitude, z.latitude] } })),
    });
  }, [recommendZones, ready, styleKey]);

  useEffect(() => {
    const map = mapSingleton.map;
    if (!map || !ready) return;
    src(map, "area")?.setData(polygonCoords && polygonCoords.length >= 3 ? {
      type: "FeatureCollection",
      features: [{ type: "Feature", properties: {},
        geometry: { type: "Polygon", coordinates: [[...polygonCoords, polygonCoords[0]]] } }],
    } : EMPTY_FC);
  }, [polygonCoords, ready, styleKey]);

  return (
    <div className="relative h-full w-full">
      <div ref={ref} className="h-full w-full" />
      {tiles === "loading" && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-ink-950/70 text-sm text-slate-300">
          Loading map…
        </div>
      )}

      {/* status badge + draw toolbar */}
      <div className="absolute left-3 top-3 z-10 flex items-center gap-2">
        <span className={`glass rounded-md px-2 py-1 text-[10px] font-medium ${tiles === "online" ? "text-mint-300" : "text-amber-300"}`}>
          {tiles === "online"
            ? `● live tiles${note ? "" : ` · ${BASEMAP_LABEL[basemap]}`}`
            : tiles === "offline" ? "● offline-safe basemap" : "…"}
          {note && <span className="ml-1 text-amber-300">⚠ {note}</span>}
        </span>
        {!drawMode ? (
          <button onClick={() => useAppStore.getState().setDrawMode("polygon")}
            className="glass flex items-center gap-1 rounded-md px-2 py-1 text-[10px] font-semibold text-teal-300 hover:bg-ink-700">
            <Pencil size={10} /> Draw area
          </button>
        ) : drawMode === "ghost" ? (
          <div className="glass flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px]">
            <span className="text-amber-300">🧪 Click the map to drop a simulated rival</span>
            <button onClick={() => useAppStore.getState().setDrawMode(false)}
              className="rounded bg-ink-700 px-1.5 py-0.5 text-slate-400">
              <X size={10} />
            </button>
          </div>
        ) : (
          <div className="glass flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px]">
            <span className="text-teal-300">✏️ {drawing} pts</span>
            <span className="text-slate-500">Enter/double-click to finish · Esc cancel</span>
            <button onClick={finishPolygon} disabled={drawing < 3}
              className="rounded bg-teal-500/20 px-1.5 py-0.5 font-bold text-teal-300 disabled:opacity-30">
              <Check size={10} />
            </button>
            <button onClick={() => { useAppStore.getState().setDrawMode(false); drawPts.current = []; setDrawing(0); updateDraft(); }}
              className="rounded bg-ink-700 px-1.5 py-0.5 text-slate-400">
              <X size={10} />
            </button>
          </div>
        )}
      </div>

      {/* basemap switcher */}
      <div className="absolute right-3 top-3 z-10 flex overflow-hidden rounded-lg border border-ink-600 bg-ink-900/85 shadow-lg backdrop-blur">
        {(["satellite", "streets", "dark"] as const).map((b) => (
          <button key={b} onClick={() => useAppStore.getState().setBasemap(b)}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-semibold transition
              ${basemap === b ? "bg-accent-500/20 text-accent-300" : "text-slate-400 hover:bg-ink-700"}`}>
            <img
              src={"data:image/svg+xml," + encodeURIComponent(
                b === "satellite"
                  ? `<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14'><rect width='14' height='14' fill='%23345241'/><rect x='2' y='2' width='5' height='5' fill='%234a7c59'/><rect x='8' y='5' width='4' height='6' fill='%236b4f3a'/><circle cx='4' cy='10' r='2' fill='%23385f46'/></svg>`
                  : b === "streets"
                  ? `<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14'><rect width='14' height='14' fill='%23e8e0d4'/><path d='M0 4h14M3 0v14M9 0v14M0 10h14' stroke='%23b9b09e' stroke-width='1'/></svg>`
                  : `<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14'><rect width='14' height='14' fill='%230f172a'/><path d='M0 5h14M4 0v14M10 0v14' stroke='%23294057' stroke-width='1'/><circle cx='7' cy='9' r='1.5' fill='%2338bdf8'/></svg>`)}
              alt="" width={14} height={14} className="rounded-[2px]" />
            {b[0].toUpperCase() + b.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
