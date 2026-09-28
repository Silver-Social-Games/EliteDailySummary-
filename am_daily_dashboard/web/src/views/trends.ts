/** Purchase Trends — last 30 days daily, or the last 8 same weekdays. */
import { esc, icon, money, compactMoney } from "./../format";
import { lineChartSvg, weekdayBarsHtml } from "./../charts";
import type { ChartLine } from "./../charts";
import { emptyState, metricBand } from "./../components";
import { getState } from "./../state";
import { paginate, tableHtml } from "./../table";
import {
  TREND, dailyDays, dayLabel, defaultSeriesIds, lastIndices, pctLabel, primarySeries,
  reportWeekday, sum, trendSeries, trendSeriesKey, weekdayIndices, windowStats,
} from "./../trend";
import type { TrendSeries } from "./../trend";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

type Mode = "daily" | "weekday";

function mode(): Mode {
  return getState("trend_mode", "daily") === "weekday" ? "weekday" : "daily";
}

function weekday(): string {
  return String(getState("trend_weekday", reportWeekday()));
}

function selectedSeries(all: TrendSeries[]): TrendSeries[] {
  const ids: string[] = getState(trendSeriesKey(), defaultSeriesIds());
  return all.filter((s) => ids.includes(s.id));
}

function rowIndices(m: Mode): number[] {
  return m === "daily" ? lastIndices() : weekdayIndices(weekday());
}

/** Table + CSV share one shape: Date, Weekday, Jackpota, Elite, Elite %, AMs. */
export function trendTableData(): { headers: string[]; rows: string[][] } {
  const t = TREND;
  if (!t) return { headers: [], rows: [] };
  const all = trendSeries();
  const ams = all.filter((s) => s.id.startsWith("am:"));
  const jp: number[] = t.jackpota || [];
  const el: number[] = t.elite || [];
  const headers = ["Date", "Weekday", "Jackpota", "Elite", "Elite %", ...ams.map((s) => s.label)];
  const rows = rowIndices(mode()).slice().reverse().map((i) => [
    String(t.dates[i]),
    String(t.weekdays?.[i] || ""),
    money(jp[i] || 0),
    money(el[i] || 0),
    jp[i] > 0 ? `${((el[i] / jp[i]) * 100).toFixed(1)}%` : "—",
    ...ams.map((s) => money(s.values[i] || 0)),
  ]);
  return { headers, rows };
}

function toolbar(m: Mode, all: TrendSeries[], selected: TrendSeries[]): string {
  const modeBtn = (id: Mode, label: string) =>
    `<button type="button" class="btn-ghost${m === id ? " active" : ""}" data-trend-mode="${id}"` +
    ` aria-pressed="${m === id ? "true" : "false"}">${label}</button>`;
  const wd = weekday();
  const picker = m === "weekday"
    ? `<span class="select-wrap"><select data-state="trend_weekday" aria-label="Weekday">` +
      WEEKDAYS.map((d) => `<option value="${d}" ${d === wd ? "selected" : ""}>${d}</option>`).join("") +
      `</select>${icon("chev-down", "ic-xs")}</span>`
    : "";
  const chips = all.map((s) => {
    const on = selected.some((x) => x.id === s.id);
    return `<button type="button" class="chip trend-chip${on ? " active" : ""}" aria-pressed="${on ? "true" : "false"}"` +
      ` data-trend-series="${esc(s.id)}"><span class="trend-dot" style="background:${s.color}"></span>${esc(s.label)}</button>`;
  }).join("");
  return `<div class="card trend-toolbar">
        <div class="toolbar">
          <div class="trend-modes">${modeBtn("daily", "Daily")}${modeBtn("weekday", "Same Weekday")}</div>
          ${picker}
          <div class="trend-series"><span class="trend-series-label">Series</span>${chips}</div>
        </div>
      </div>`;
}

function band(primary: TrendSeries): string {
  const days = dailyDays();
  const st = windowStats(primary.values, days);
  const wd = weekday();
  const wdIdx = weekdayIndices(wd);
  const wdAvg = wdIdx.length ? sum(wdIdx.map((i) => primary.values[i] || 0)) / wdIdx.length : 0;
  const pct = pctLabel(st.pct);
  const pctTone = st.pct == null ? "neutral" : st.pct >= 0 ? "success" : "danger";
  return metricBand(`${primary.label} · Purchase Trend`, [
    { label: `${days}D Purchase`, value: compactMoney(st.total) },
    { label: "Daily Avg", value: compactMoney(st.avg) },
    { label: "Best Day", value: compactMoney(st.bestValue), foot: esc(dayLabel(st.bestIndex)) },
    { label: `vs Prior ${days}D`, value: pct, tone: pctTone },
    { label: `${wd} Avg (Last ${wdIdx.length})`, value: compactMoney(wdAvg) },
  ], { cols: 5 });
}

function chart(m: Mode, shown: TrendSeries[]): string {
  if (!shown.length) {
    return `<div class="card"><div class="card-body t-tertiary t-small">Pick at least one series.</div></div>`;
  }
  if (m === "daily") {
    const idx = lastIndices();
    const isAm = (s: TrendSeries) => s.id.startsWith("am:");
    const anyAm = shown.some(isAm);
    const hint = anyAm && shown.some((s) => s.id === "jackpota")
      ? `<div class="trend-hint t-tertiary t-small">Hide Jackpota to spread the AM lines</div>`
      : "";
    const drawOrder = [...shown.filter((s) => s.id !== "elite"), ...shown.filter((s) => s.id === "elite")];
    const lines: ChartLine[] = drawOrder.map((s) => ({
      label: s.label,
      values: idx.map((i) => s.values[i] || 0),
      color: s.color,
      width: s.id === "elite" || isAm(s) ? 2.5 : 2,
      dashed: s.id === "jackpota",
    }));
    return `<div class="card gold-top trend-chart-card">
          <div class="card-head">
            <span class="card-icon">${icon("trend-up", "ic-sm")}</span>
            <div><div class="card-title">Last ${idx.length} Days · Daily Purchase</div>
            <div class="card-sub">Hover a day to see its values</div></div>
          </div>
          <div class="card-body">
            ${lineChartSvg(lines, idx.map((i) => dayLabel(i, false)), {
              height: 280, endLabels: true, readoutLabels: idx.map((i) => dayLabel(i)),
            })}
            ${hint}
          </div>
        </div>`;
  }
  const wd = weekday();
  const idx = weekdayIndices(wd);
  const cards = shown.map((s) =>
    weekdayBarsHtml(s.label, s.color, idx.map((i) => s.values[i] || 0), idx.map((i) => dayLabel(i, false)))
  ).join("");
  return `<div class="card gold-top trend-chart-card">
        <div class="card-head">
          <span class="card-icon">${icon("calendar", "ic-sm")}</span>
          <div><div class="card-title">Last ${idx.length} ${esc(wd)}s · Same Weekday</div>
          <div class="card-sub">Latest week in gold · pill = change vs the prior ${esc(wd)}</div></div>
        </div>
        <div class="card-body wk-grid">${cards}</div>
      </div>`;
}

function table(m: Mode): string {
  const { headers, rows } = trendTableData();
  const { slice, pager, total } = paginate(rows.map((cells) => ({ cells })), `trend_tbl_${m}`);
  const align = headers.map((_, i) => (i < 2 ? "left" : "right"));
  return `<div class="card">
        <div class="card-head table-section-head"><div class="card-title">${m === "daily" ? "Daily Purchase" : `${esc(weekday())} Purchase`}</div></div>
        ${tableHtml(headers, slice.map((r) => (r.cells as string[]).map(esc)), align, undefined,
          { empty: "No trend data.", tableClass: "trend-grid" })}
        ${total ? pager : ""}
      </div>`;
}

export function viewTrends(): string {
  const primary = primarySeries();
  if (!TREND || !primary) {
    return emptyState("trend-up", "No Purchase Trend Yet",
      "This brief was generated before Purchase Trends existed. Re-run the generator for this date.");
  }
  const m = mode();
  const all = trendSeries();
  const shown = selectedSeries(all);
  return `<div class="stack trends-view">
        ${toolbar(m, all, shown)}
        ${band(primary)}
        ${chart(m, shown)}
        ${table(m)}
      </div>`;
}
