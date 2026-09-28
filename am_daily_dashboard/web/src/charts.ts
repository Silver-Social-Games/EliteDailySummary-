/** Lightweight SVG charts — no external library. */
import { esc, compactMoney, money } from "./format";
import { wowPillHtml } from "./cells";

export const BAR_COLORS = [
  "#6366F1", "#0E9F6E", "#3B82F6", "#D97706", "#8B5CF6", "#E11D48",
  "#14B8A6", "#F59E0B", "#64748B", "#EC4899",
];

export interface ChartLine {
  label: string;
  values: number[];
  color: string;
  width?: number;
  dashed?: boolean;
}

/** Round tick step for ~5 intervals, and the smallest multiple of it that
 *  holds `v` — a tight top, so small series keep their share of the height. */
function niceScale(v: number): { max: number; step: number } {
  if (!(v > 0)) return { max: 1, step: 0.25 };
  const raw = v / 5;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const m = raw / p;
  const step = (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  return { max: Math.ceil(v / step) * step, step };
}

function pathD(values: number[], x: (i: number) => number, y: (v: number) => number): string {
  return values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
}

function lineAttrs(l: ChartLine, fallbackWidth: number): string {
  return `fill="none" stroke="${esc(l.color)}" stroke-width="${l.width ?? fallbackWidth}"` +
    ` stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"` +
    (l.dashed ? ` stroke-dasharray="3 3"` : "");
}

/** Axis-free sparkline. Each line is scaled to its own range, so a book and
 *  the whole platform can share one panel and both show their shape. */
export function sparklineSvg(lines: ChartLine[], w = 300, h = 64): string {
  const pad = 3;
  const paths = lines.map((l) => {
    const vals = l.values;
    if (!vals.length) return "";
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const span = hi - lo || 1;
    const x = (i: number) => (vals.length <= 1 ? w / 2 : (i * w) / (vals.length - 1));
    const y = (v: number) => pad + (h - 2 * pad) * (1 - (v - lo) / span);
    return `<path d="${pathD(vals, x, y)}" ${lineAttrs(l, 1.5)}></path>`;
  }).join("");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">${paths}</svg>`;
}

export interface LineChartOptions {
  height?: number;
  /** Rotated left-axis title. */
  axisTitle?: string;
  /** Name + latest value at each line's right end. */
  endLabels?: boolean;
  /** A value label on every point; only drawn for 1–2 lines. */
  pointValues?: boolean;
}

const END_LABEL_GAP = 14;

/** Spread label y's at least `gap` apart inside [lo, hi], keeping their order. */
function spreadLabels(ys: number[], gap: number, lo: number, hi: number): number[] {
  const order = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  const out = order.map((o) => Math.min(hi, Math.max(lo, o.y)));
  for (let k = 1; k < out.length; k++) out[k] = Math.max(out[k], out[k - 1] + gap);
  if (out.length && out[out.length - 1] > hi) {
    out[out.length - 1] = hi;
    for (let k = out.length - 2; k >= 0; k--) out[k] = Math.min(out[k], out[k + 1] - gap);
  }
  const res: number[] = new Array(ys.length);
  order.forEach((o, k) => { res[o.i] = out[k]; });
  return res;
}

function shortValue(v: number): string {
  return compactMoney(v).replace(/^\$/, "");
}

/** Multi-series line chart on ONE linear $ axis from 0, so every line's
 *  height is proportional to its dollars — never add a second axis. One hover
 *  column per point whose native tooltip lists every series. */
export function lineChartSvg(lines: ChartLine[], labels: string[], opts: LineChartOptions = {}): string {
  const W = 960;
  const H = opts.height ?? 340;
  const showValues = !!opts.pointValues && lines.length > 0 && lines.length <= 2;
  const pl = opts.axisTitle ? 78 : 62;
  const pr = opts.endLabels ? 132 : 18;
  const pt = showValues ? 22 : 14;
  const pb = showValues ? 44 : 30;
  const iw = W - pl - pr;
  const ih = H - pt - pb;
  const base = pt + ih;
  const n = labels.length;
  const x = (i: number) => pl + (n <= 1 ? iw / 2 : (i * iw) / (n - 1));
  const { max, step: tick } = niceScale(Math.max(0, ...lines.flatMap((l) => l.values)));
  const y = (v: number) => base - (max > 0 ? (Math.max(0, v) / max) * ih : 0);

  let grid = "";
  const ticks = Math.round(max / tick);
  for (let k = 0; k <= ticks; k++) {
    const yy = base - (k / ticks) * ih;
    grid += `<line class="lc-grid" x1="${pl}" x2="${W - pr}" y1="${yy}" y2="${yy}"></line>`;
    grid += `<text class="lc-axis lc-tick" x="${pl - 8}" y="${yy + 4}" text-anchor="end">${esc(compactMoney(tick * k))}</text>`;
  }
  if (opts.axisTitle) {
    grid += `<text class="lc-axis-title" x="14" y="${pt + ih / 2}" text-anchor="middle"` +
      ` transform="rotate(-90 14 ${pt + ih / 2})">${esc(opts.axisTitle)}</text>`;
  }
  const step = Math.max(1, Math.ceil(n / 8));
  let xl = "";
  labels.forEach((lab, i) => {
    const last = i === n - 1;
    if ((i % step === 0 && (last || n - 1 - i >= step / 2)) || last) {
      xl += `<text class="lc-axis" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(lab)}</text>`;
    }
  });

  const paths = lines.map((l) => {
    if (!l.values.length) return "";
    const lastI = l.values.length - 1;
    const v = l.values[lastI] || 0;
    return `<path d="${pathD(l.values, x, y)}" ${lineAttrs(l, 2)}></path>` +
      `<circle class="lc-last" cx="${x(lastI).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3.5" fill="${esc(l.color)}"` +
      ` data-v="${v}"></circle>`;
  }).join("");

  let values = "";
  if (showValues) {
    lines.forEach((l, li) => {
      const other = lines[1 - li];
      l.values.forEach((v, i) => {
        const above = !other || (v || 0) >= (other.values[i] || 0);
        const cy = y(v || 0);
        values += `<circle class="lc-dot" cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="2" fill="${esc(l.color)}"></circle>` +
          `<text class="lc-val" x="${x(i).toFixed(1)}" y="${(above ? cy - 8 : cy + 15).toFixed(1)}"` +
          ` text-anchor="middle" fill="${esc(l.color)}">${esc(shortValue(v || 0))}</text>`;
      });
    });
  }

  let ends = "";
  if (opts.endLabels) {
    const lastY = lines.map((l) => y(l.values[l.values.length - 1] || 0));
    const ly = spreadLabels(lastY, END_LABEL_GAP, pt + 4, base);
    const lx = W - pr + 14;
    lines.forEach((l, i) => {
      if (!l.values.length) return;
      const px = x(l.values.length - 1);
      if (Math.abs(ly[i] - lastY[i]) > 1) {
        ends += `<polyline class="lc-leader" points="${(px + 5).toFixed(1)},${lastY[i].toFixed(1)} ${(lx - 8).toFixed(1)},${lastY[i].toFixed(1)} ${(lx - 3).toFixed(1)},${ly[i].toFixed(1)}"` +
          ` stroke="${esc(l.color)}"></polyline>`;
      }
      ends += `<text class="lc-end" x="${lx}" y="${(ly[i] + 4).toFixed(1)}" fill="${esc(l.color)}">` +
        `${esc(l.label)} <tspan class="lc-end-v">${esc(compactMoney(l.values[l.values.length - 1] || 0))}</tspan></text>`;
    });
  }

  const colW = n > 1 ? iw / (n - 1) : iw;
  const hits = labels.map((lab, i) => {
    const rows = lines.slice().sort((a, b) => (b.values[i] || 0) - (a.values[i] || 0))
      .map((l) => `${l.label}: ${money(l.values[i] || 0)}`);
    const tip = [lab, ...rows].join("\n");
    return `<rect class="lc-hit" x="${(x(i) - colW / 2).toFixed(1)}" y="${pt}" width="${colW.toFixed(1)}" height="${ih}">` +
      `<title>${esc(tip)}</title></rect>`;
  }).join("");

  return `<svg class="line-chart" viewBox="0 0 ${W} ${H}" data-base="${base.toFixed(1)}" role="img" aria-label="Purchase trend chart">
        ${grid}${xl}${paths}${values}${ends}${hits}
      </svg>`;
}

/** Same-weekday bars: one column per week, WoW pill vs the prior week, the
 *  latest week in gold and earlier weeks muted. */
export function weekdayBarsHtml(title: string, color: string, values: number[], labels: string[]): string {
  const max = Math.max(1, ...values);
  const cols = values.map((v, i) => {
    const prev = i > 0 ? values[i - 1] : 0;
    const pct = i > 0 && prev > 0 ? ((v - prev) / prev) * 100 : null;
    const pill = pct == null ? wowPillHtml("") : wowPillHtml(`${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`);
    const latest = i === values.length - 1;
    const h = Math.max(2, (v / max) * 100);
    return `<div class="wk-col${latest ? " latest" : ""}">
          <div class="wk-val">${esc(compactMoney(v))}</div>
          <div class="wk-track"><span class="wk-bar" style="height:${h.toFixed(1)}%"></span></div>
          <div class="wk-label">${esc(labels[i] || "")}</div>
          ${pill}
        </div>`;
  }).join("");
  return `<div class="wk-card">
        <div class="wk-title"><span class="trend-dot" style="background:${esc(color)}"></span>${esc(title)}</div>
        <div class="wk-bars">${cols}</div>
      </div>`;
}
