/** Purchase trend series and window stats — shared by the hero panel, the
 *  Purchase Trends view, its click wiring and its CSV export. */
import type { Dict } from "./types";
import { AGENTS, HIDE_MANAGER, REPORT } from "./payload";
import { app } from "./state";
import { BAR_COLORS } from "./charts";

export interface TrendSeries {
  id: string;
  label: string;
  values: number[];
  color: string;
}

export const GOLD = "#D4AF37";
export const MUTED = "#9490A0";

/** Fixed per AM so a line keeps its colour whatever the order; clear of GOLD and MUTED. */
const AM_COLORS: Record<string, string> = {
  coral: "#E11D48",
  gabriel: "#2563EB",
  lee: "#059669",
  rachel: "#7C3AED",
  alon: "#EA580C",
};

export function amColor(name: string, i: number): string {
  return AM_COLORS[String(name).trim().toLowerCase()] || BAR_COLORS[i % BAR_COLORS.length];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Absent from briefs generated before Purchase Trends shipped. */
export const TREND: Dict | null =
  REPORT.purchaseTrend && Array.isArray(REPORT.purchaseTrend.dates) && REPORT.purchaseTrend.dates.length
    ? REPORT.purchaseTrend
    : null;

export function trendSeries(): TrendSeries[] {
  if (!TREND) return [];
  const out: TrendSeries[] = [
    { id: "elite", label: "Elite", values: TREND.elite || [], color: GOLD },
    { id: "jackpota", label: "Jackpota", values: TREND.jackpota || [], color: MUTED },
  ];
  AGENTS.forEach((a, i) => {
    const values = a.purchaseTrend?.values;
    if (Array.isArray(values)) {
      out.push({ id: `am:${a.agentName}`, label: a.agentName, values,
        color: amColor(a.agentName, i) });
    }
  });
  return out;
}

export function seriesById(id: string): TrendSeries | undefined {
  return trendSeries().find((s) => s.id === id);
}

/** Manager reads Elite first; an AM file reads their own book first. */
export function primarySeries(): TrendSeries | undefined {
  return (HIDE_MANAGER ? seriesById(`am:${app.agent}`) : undefined) || seriesById("elite");
}

export function trendSeriesKey(): string {
  return HIDE_MANAGER ? `trend_series_${app.agent}` : "trend_series";
}

export function defaultSeriesIds(): string[] {
  return HIDE_MANAGER ? [`am:${app.agent}`, "elite"] : ["elite", "jackpota"];
}

export function sum(values: number[]): number {
  return values.reduce((s, v) => s + (Number(v) || 0), 0);
}

export function dailyDays(): number {
  return Number(TREND?.dailyDays) || 30;
}

export interface WindowStats {
  total: number;
  avg: number;
  pct: number | null;
  bestIndex: number;
  bestValue: number;
}

/** Last `days` vs the `days` before them, on indices into TREND.dates. */
export function windowStats(values: number[], days = dailyDays()): WindowStats {
  const n = values.length;
  const start = Math.max(0, n - days);
  const last = values.slice(start);
  const prior = values.slice(Math.max(0, n - 2 * days), start);
  const total = sum(last);
  const priorTotal = prior.length === days ? sum(prior) : 0;
  let bestIndex = start;
  for (let i = start; i < n; i++) if ((values[i] || 0) > (values[bestIndex] || 0)) bestIndex = i;
  return {
    total,
    avg: last.length ? total / last.length : 0,
    pct: priorTotal > 0 ? ((total - priorTotal) / priorTotal) * 100 : null,
    bestIndex,
    bestValue: values[bestIndex] || 0,
  };
}

export function pctLabel(p: number | null): string {
  if (p == null || !Number.isFinite(p)) return "—";
  return `${p >= 0 ? "+" : ""}${p.toFixed(1)}%`;
}

/** "Thu 18 Sep" from an index into TREND.dates, with no Date timezone shifts. */
export function dayLabel(i: number, withWeekday = true): string {
  const iso = String(TREND?.dates?.[i] || "");
  if (!iso) return "";
  const body = `${Number(iso.slice(8, 10))} ${MONTHS[Number(iso.slice(5, 7)) - 1] || ""}`;
  return withWeekday ? `${TREND?.weekdays?.[i] || ""} ${body}`.trim() : body;
}

export function lastIndices(days = dailyDays()): number[] {
  const n = TREND?.dates?.length || 0;
  const out: number[] = [];
  for (let i = Math.max(0, n - days); i < n; i++) out.push(i);
  return out;
}

/** The last `weeks` indices falling on `weekday` ("Mon".."Sun"), oldest first. */
export function weekdayIndices(weekday: string, weeks = 8): number[] {
  const wd: string[] = TREND?.weekdays || [];
  const hits = wd.map((w, i) => (w === weekday ? i : -1)).filter((i) => i >= 0);
  return hits.slice(-weeks);
}

export function reportWeekday(): string {
  const wd: string[] = TREND?.weekdays || [];
  return String(REPORT.dayShort || wd[wd.length - 1] || "Mon");
}
