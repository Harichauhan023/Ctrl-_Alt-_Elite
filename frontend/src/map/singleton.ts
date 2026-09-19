import type maplibregl from "maplibre-gl";

/** Tiny module singleton so any component can drive the map (flyTo etc.). */
export const mapSingleton: { map: maplibregl.Map | null } = { map: null };

export function flyToSite(lat: number, lng: number, zoom = 14) {
  mapSingleton.map?.flyTo({ center: [lng, lat], zoom, speed: 1.4 });
}
