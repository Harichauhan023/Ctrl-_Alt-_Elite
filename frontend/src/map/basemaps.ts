// Shared basemap definitions — REAL geographic tiles in every mode:
// dark = OpenFreeMap vector, streets = OpenStreetMap raster, satellite = Esri imagery (+labels).
export const STYLE_DARK = "https://tiles.openfreemap.org/styles/dark";
export const GLYPHS = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf";

export const OFFLINE_STYLE: any = {
  version: 8, name: "offline-safe", sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#0a0f1c" } }],
};

export const STYLE_STREETS: any = {
  version: 8, name: "streets-osm", glyphs: GLYPHS,
  sources: { osm: { type: "raster", tileSize: 256, maxzoom: 19,
    tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
    attribution: "© OpenStreetMap contributors" } },
  layers: [{ id: "osm-tiles", type: "raster", source: "osm",
    paint: { "raster-saturation": -0.1 } }],
};

export const STYLE_SATELLITE: any = {
  version: 8, name: "satellite-esri", glyphs: GLYPHS,
  sources: {
    esri: { type: "raster", tileSize: 256, maxzoom: 18,
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      attribution: "Imagery © Esri, Maxar, Earthstar Geographics" },
    esri_labels: { type: "raster", tileSize: 256, maxzoom: 18,
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"] },
  },
  layers: [
    { id: "esri-tiles", type: "raster", source: "esri" },
    { id: "esri-labels", type: "raster", source: "esri_labels", paint: { "raster-opacity": 0.85 } },
  ],
};

export const BASEMAP_MAP: Record<string, any> = {
  dark: STYLE_DARK, streets: STYLE_STREETS, satellite: STYLE_SATELLITE,
};
export const BASEMAP_LABEL: Record<string, string> = {
  dark: "Dark (OpenFreeMap)", streets: "Streets (OSM)", satellite: "Satellite (Esri)",
};
export const isRaster = (b: string) => b === "streets" || b === "satellite";

// Chain used when a basemap's tiles are unreachable on the viewer's network:
// dark (vector) → streets (OSM raster) → satellite (Esri raster) → offline-safe.
export const BASEMAP_FALLBACK: Record<string, string> = {
  dark: "streets", streets: "satellite", satellite: "offline",
};
export const styleFor = (id: string): any =>
  id === "offline" ? OFFLINE_STYLE : (BASEMAP_MAP[id] ?? OFFLINE_STYLE);
