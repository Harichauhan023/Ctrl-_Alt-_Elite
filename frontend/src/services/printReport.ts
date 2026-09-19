import type { AnalysisResult, CatchmentResponse, ExplainResponse } from "../types";
import { FACTOR_KEYS, FACTOR_META } from "../store/useAppStore";

/** Opens a clean printable report in a new window (user can Save-as-PDF). */
export function printReport(
  analysis: AnalysisResult,
  catchment?: CatchmentResponse | null,
  explanation?: ExplainResponse | null,
) {
  const w = window.open("", "_blank", "width=820,height=1000");
  if (!w) return;
  const s = analysis.scores;
  const d = analysis.details || {};
  const row = (k: string, v: any) =>
    `<tr><td style="padding:6px 10px;border:1px solid #ddd;color:#555">${k}</td>
     <td style="padding:6px 10px;border:1px solid #ddd;font-weight:600">${v}</td></tr>`;

  w.document.write(`<!doctype html><html><head><title>GeoReady-AI Report — ${analysis.name || "candidate pin"}</title>
  <style>body{font-family:Inter,system-ui,sans-serif;color:#111;padding:32px;max-width:760px;margin:auto}
  h1{font-size:22px;margin:0}h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#0284c7;margin:26px 0 8px}
  table{border-collapse:collapse;width:100%;font-size:13px}.badge{display:inline-block;padding:3px 10px;border-radius:999px;
  background:${analysis.status === "NOT_SUITABLE" ? "#fee2e2" : "#dcfce7"};font-weight:700;font-size:12px}
  li{font-size:13px;margin:3px 0}.meta{color:#777;font-size:11px}@media print{button{display:none}}</style></head><body>
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div><h1>GeoReady-AI · Site Analysis Report</h1>
    <div class="meta">Rajkot study area · generated ${new Date().toLocaleString()} · Bit N Build '26 PS-2</div></div>
    <button onclick="window.print()" style="padding:8px 14px">Print / Save PDF</button></div>

  <h2>Site</h2>
  <table>${row("Name", analysis.name || "Candidate pin")}${row("Business", analysis.business_label)}
  ${row("Coordinates", `${analysis.latitude.toFixed(5)}, ${analysis.longitude.toFixed(5)}`)}
  ${row("Overall readiness", `<b style="font-size:18px">${analysis.overall_score} / 100</b> &nbsp; <span class="badge">${(analysis.status ?? "").replaceAll("_", " ")}</span>`)}
  </table>

  ${analysis.constraints?.length ? `<h2>Hard constraints</h2><ul>${analysis.constraints.map((c) => `<li style="color:#b91c1c">⛔ ${c}</li>`).join("")}</ul>` : ""}

  <h2>Factor scores (weighted)</h2>
  <table>${FACTOR_KEYS.map((k) => row(`${FACTOR_META[k].label} (weight ${Math.round(analysis.weights[k] * 100)}%)`, `${s[k]} / 100`)).join("")}</table>

  <h2>Key metrics</h2>
  <table>
    ${row("Population within 1 km", d.population?.population_within_1km?.toLocaleString?.() ?? "—")}
    ${row("Nearest major road", `${d.accessibility?.nearest_major_road_km ?? "—"} km`)}
    ${row("Competitors (1 km / 3 km)", `${d.competition?.competitors_within_1km ?? 0} / ${d.competition?.competitors_within_3km ?? 0}`)}
    ${row("Nearest competitor", `${d.competition?.nearest_competitor_km ?? "—"} km`)}
    ${row("Land use", d.land_use?.land_use_category ?? "—")}
    ${row("Environmental risk", d.environment?.risk_level ?? "low")}
  </table>

  <h2>Reasons & risks</h2>
  <ul>${(analysis.reasons || []).map((r) => `<li style="color:#166534">✔ ${r}</li>`).join("")}
      ${(analysis.risks || []).map((r) => `<li style="color:#b45309">⚠ ${r}</li>`).join("")}</ul>

  ${catchment ? `<h2>Catchment (approx. ${catchment.method})</h2><table>
    ${catchment.catchments.map((c) => row(`${c.minutes}-minute travel shed`,
      `${c.reachable_population.toLocaleString()} people · ${c.competitors_in_range} competitors`)).join("")}</table>` : ""}

  ${explanation ? `<h2>AI explanation (${explanation.meta.used_llm ? `Gemini · ${explanation.meta.provider}` : "deterministic"})</h2>
    <p style="font-size:13px">${explanation.explanation.summary}</p>
    <p style="font-size:13px"><b>Key reason:</b> ${explanation.explanation.key_reason}</p>
    <div class="meta">RAG (${explanation.meta.rag_mode}): ${(explanation.meta.rag_sources || []).join(" · ")}</div>` : ""}

  <h2>Methodology</h2>
  <p class="meta">Deterministic weighted-sum scoring over five 0–100 normalised factors with exponential
  distance decay; hard constraints override the numeric score. Data: OpenStreetMap roads &amp; POIs + clearly
  labelled synthetic population / land-use / risk layers for the Rajkot study area. Same input + same weights ⇒ same score.</p>
  </body></html>`);
  w.document.close();
  setTimeout(() => w.focus(), 300);
}
