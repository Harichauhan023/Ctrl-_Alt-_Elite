import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../services/api";

const TT = { background: "#0d1424", border: "1px solid #243356", borderRadius: 8, fontSize: 11 } as const;
const LANDUSE_COLORS: Record<string, string> = {
  commercial: "#d97706", mixed_use: "#8b5cf6", industrial: "#57534e",
  residential: "#0e7490", agricultural: "#4d7c0f", protected: "#b91c1c", unknown: "#334155",
};
const RISK_COLORS: Record<string, string> = { low: "#22c55e", medium: "#f59e0b", high: "#ea580c", critical: "#7f1d1d" };

function hav(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371, p = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * p / 2) ** 2 + Math.cos(lat1 * p) * Math.cos(lat2 * p) * Math.sin((lon2 - lon1) * p / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

export default function Analytics() {
  const [pop, setPop] = useState<GeoJSON.FeatureCollection | null>(null);
  const [hot, setHot] = useState<GeoJSON.FeatureCollection | null>(null);
  const [land, setLand] = useState<GeoJSON.FeatureCollection | null>(null);
  const [risk, setRisk] = useState<GeoJSON.FeatureCollection | null>(null);
  const [comps, setComps] = useState<GeoJSON.FeatureCollection | null>(null);
  const [sites, setSites] = useState<any[]>([]);

  useEffect(() => {
    api.layerData("population").then(setPop).catch(() => {});
    api.hotspots("EV_CHARGING").then((d) => setHot(d.geojson)).catch(() => {});
    api.layerData("landuse").then(setLand).catch(() => {});
    api.layerData("risk").then(setRisk).catch(() => {});
    api.layerData("competitors").then(setComps).catch(() => {});
    api.sites().then((d) => setSites(d.sites)).catch(() => {});
  }, []);

  const popHist = useMemo(() => {
    if (!pop) return [];
    const bins = Array.from({ length: 8 }, (_, i) => ({ range: `${i * 4}–${(i + 1) * 4}k`, cells: 0, people: 0 }));
    for (const f of pop.features) {
      const d = (f.properties as any).density ?? 0;
      const i = Math.min(7, Math.floor(d / 4000));
      bins[i].cells++;
      bins[i].people += (f.properties as any).population ?? 0;
    }
    return bins;
  }, [pop]);

  const readyHist = useMemo(() => {
    if (!hot) return [];
    const bins = Array.from({ length: 10 }, (_, i) => ({ range: `${i * 10}`, zones: 0, fill: "#38bdf8" }));
    for (const f of hot.features) {
      const o = (f.properties as any).overall ?? 0;
      bins[Math.min(9, Math.floor(o / 10))].zones++;
    }
    bins.forEach((b, i) => (b.fill = ["#ef4444", "#f97316", "#f59e0b", "#eab308", "#a3e635", "#84cc16", "#4ade80", "#22c55e", "#16a34a", "#15803d"][i]));
    return bins;
  }, [hot]);

  const landShare = useMemo(() => {
    if (!land) return [];
    const m = new Map<string, number>();
    for (const f of land.features) {
      const c = (f.properties as any).category ?? "unknown";
      m.set(c, (m.get(c) ?? 0) + 1);
    }
    return [...m.entries()].map(([name, value]) => ({ name, value }));
  }, [land]);

  const riskShare = useMemo(() => {
    if (!risk) return [];
    const m = new Map<string, number>();
    for (const f of risk.features) {
      const c = (f.properties as any).risk_level ?? "medium";
      m.set(c, (m.get(c) ?? 0) + 1);
    }
    return [...m.entries()].map(([name, value]) => ({ name, value }));
  }, [risk]);

  const compPerSite = useMemo(() => {
    if (!comps || !sites.length) return [];
    const pts = comps.features.map((f) => (f.geometry as any).coordinates as number[]);
    return sites.map((s) => ({
      name: s.name.length > 14 ? s.name.slice(0, 13) + "…" : s.name,
      within1km: pts.filter(([lon, lat]) => hav(s.latitude, s.longitude, lat, lon) <= 1).length,
      within3km: pts.filter(([lon, lat]) => hav(s.latitude, s.longitude, lat, lon) <= 3).length,
    }));
  }, [comps, sites]);

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="mx-auto max-w-6xl">
        <h1 className="text-xl font-bold tracking-tight">Layer Analytics</h1>
        <p className="mt-0.5 text-xs text-slate-400">
          What's actually inside the Rajkot geospatial stack — no black boxes.
        </p>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Chart title="Population density model (H3 cells)">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={popHist}>
                <CartesianGrid stroke="#1a2540" vertical={false} />
                <XAxis dataKey="range" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <Tooltip contentStyle={TT} formatter={(v: any, n: any) => [typeof v === "number" ? v.toLocaleString() : v, n === "people" ? "people" : "cells"]} />
                <Bar dataKey="people" fill="#38bdf8" radius={[3, 3, 0, 0]} name="people" />
              </BarChart>
            </ResponsiveContainer>
          </Chart>

          <Chart title="Zone readiness histogram (EV defaults)">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={readyHist}>
                <CartesianGrid stroke="#1a2540" vertical={false} />
                <XAxis dataKey="range" tick={{ fill: "#94a3b8", fontSize: 10 }} label={{ value: "readiness band", position: "insideBottom", offset: -2, fill: "#64748b", fontSize: 9 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <Tooltip contentStyle={TT} />
                <Bar dataKey="zones" radius={[3, 3, 0, 0]}>
                  {readyHist.map((b, i) => <Cell key={i} fill={b.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Chart>

          <Chart title="Land-use zone mix (synthetic, city-typical)">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={landShare} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false} fontSize={9}>
                  {landShare.map((e, i) => <Cell key={i} fill={LANDUSE_COLORS[e.name] ?? "#334155"} />)}
                </Pie>
                <Tooltip contentStyle={TT} />
              </PieChart>
            </ResponsiveContainer>
          </Chart>

          <Chart title="Environmental risk coverage (Aji flood model)">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={riskShare} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false} fontSize={9}>
                  {riskShare.map((e, i) => <Cell key={i} fill={RISK_COLORS[e.name] ?? "#334155"} />)}
                </Pie>
                <Tooltip contentStyle={TT} />
              </PieChart>
            </ResponsiveContainer>
          </Chart>

          <Chart title="Competitor pressure per candidate site" full>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={compPerSite}>
                <CartesianGrid stroke="#1a2540" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} interval={0} angle={-18} textAnchor="end" height={50} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} allowDecimals={false} />
                <Tooltip contentStyle={TT} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="within1km" name="within 1 km" fill="#ef4444" stackId="a" radius={[0, 0, 0, 0]} />
                <Bar dataKey="within3km" name="within 3 km" fill="#f59e0b" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Chart>
        </div>
      </div>
    </div>
  );
}

function Chart({ title, children, full }: { title: string; children: React.ReactNode; full?: boolean }) {
  return (
    <div className={`glass rounded-xl p-4 ${full ? "lg:col-span-2" : ""}`}>
      <div className="panel-title mb-3">{title}</div>
      {children}
    </div>
  );
}
