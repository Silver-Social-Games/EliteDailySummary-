/** Lightweight SVG charts — no external library. */
import type { Dict } from "./types";
import { esc } from "./format";

const BAR_COLORS = [
  "#6366F1", "#0E9F6E", "#3B82F6", "#D97706", "#8B5CF6", "#E11D48",
  "#14B8A6", "#F59E0B", "#64748B", "#EC4899",
];

type GeoSlice = Dict & { state: string; bettors: number; share: number };

type GeoNormalized = {
  named: GeoSlice[];
  other: GeoSlice | null;
  otherKnown: number;
  otherUnknown: number;
  total: number;
};

/** Merge UNKNOWN sign-in state into Other so the chart matches the export file. */
function normalizeGeoSlices(slices: Dict[]): GeoNormalized {
  const rows = slices.filter((sl) => String(sl.state || "").toUpperCase() !== "TOTAL");
  let unknown = 0;
  let knownOther = 0;
  const named: GeoSlice[] = [];
  for (const sl of rows) {
    const state = String(sl.state || "").trim();
    const bettors = Number(sl.bettors) || 0;
    if (state.toUpperCase() === "UNKNOWN") {
      unknown += bettors;
      continue;
    }
    if (state === "Other") {
      knownOther += bettors;
      continue;
    }
    named.push({ ...sl, state, bettors, share: 0 });
  }
  named.sort((a, b) => b.bettors - a.bettors);
  const otherBettors = knownOther + unknown;
  const other: GeoSlice | null = otherBettors
    ? { state: "Other", bettors: otherBettors, share: 0 }
    : null;
  const total = named.reduce((s, x) => s + x.bettors, 0) + (other?.bettors || 0);
  const withShare = (sl: GeoSlice): GeoSlice => ({
    ...sl,
    share: total > 0 ? Math.round((sl.bettors / total) * 1000) / 10 : 0,
  });
  return {
    named: named.map(withShare),
    other: other ? withShare(other) : null,
    otherKnown: knownOther,
    otherUnknown: unknown,
    total,
  };
}

function geoBarRow(sl: GeoSlice, i: number, maxShare: number, summary = false): string {
  const pct = Number(sl.share) || 0;
  const width = summary ? Math.min(100, Math.max(4, (pct / maxShare) * 100)) : Math.max(4, (pct / maxShare) * 100);
  const color = summary ? "var(--ink-4)" : BAR_COLORS[i % BAR_COLORS.length];
  const rowCls = summary ? "geo-bar-row geo-bar-row-other" : "geo-bar-row";
  const fillCls = summary ? "geo-bar-fill geo-bar-fill-muted" : "geo-bar-fill";
  return `<div class="${rowCls}">
          <span class="geo-bar-label">${esc(String(sl.state))}</span>
          <div class="geo-bar-track"><span class="${fillCls}" style="width:${width.toFixed(1)}%;background:${color}"></span></div>
          <span class="geo-bar-pct">${pct.toFixed(1)}%</span>
          <span class="geo-bar-count">${(Number(sl.bettors) || 0).toLocaleString()}</span>
        </div>`;
}

export function donutChartHtml(chart: Dict | null | undefined): string {
  if (!chart || !chart.slices || !chart.slices.length) {
    return `<div class="segment-panel geo-panel empty">
        <div class="segment-panel-head">
          <span class="segment-panel-title">${esc(chart?.title || "Elite Player by State")}</span>
        </div>
        <div class="segment-empty t-tertiary t-small">No state data.</div>
      </div>`;
  }
  const geo = normalizeGeoSlices(chart.slices || []);
  if (!geo.total) {
    return `<div class="segment-panel geo-panel empty">
        <div class="segment-panel-head">
          <span class="segment-panel-title">${esc(chart.title || "Elite Player by State")}</span>
        </div>
        <div class="segment-empty t-tertiary t-small">No state data.</div>
      </div>`;
  }
  const topNamed = geo.named.slice(0, 8);
  const barRows = geo.other ? [...topNamed, geo.other] : topNamed;
  const maxShare = Math.max(...barRows.map((sl) => Number(sl.share) || 0), 1);
  const bars = topNamed.map((sl, i) => geoBarRow(sl, i, maxShare)).join("");
  const otherBar = geo.other
    ? geoBarRow(geo.other, topNamed.length, maxShare, true)
    : "";
  return `<div class="segment-panel geo-panel">
        <div class="segment-panel-head">
          <span class="segment-panel-title">${esc(chart.title || "Elite Player by State")}</span>
        </div>
        <div class="geo-bar-chart">
          <div class="geo-bar-head t-small t-tertiary"><span>State</span><span>Share</span><span>Players</span></div>
          ${bars}
          ${otherBar}
        </div>
      </div>`;
}
