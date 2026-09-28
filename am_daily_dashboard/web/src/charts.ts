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
  /** Name + latest value at each line's right end. */
  endLabels?: boolean;
  /** Per-day labels for the readout strip above the plot ("Sat 13 Sep"); on
   *  hover the strip shows that day's values, at rest the latest day's. */
  readoutLabels?: string[];
}

const END_LABEL_GAP = 12;

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

/** One readout line: the day, then every series high to low with its colour dot. */
function readoutText(cls: string, x0: number, yy: number, day: string, lines: ChartLine[], i: number): string {
  const rows = lines.slice().sort((a, b) => (b.values[i] || 0) - (a.values[i] || 0));
  const parts = rows.map((l) =>
    `<tspan dx="14" fill="${esc(l.color)}">●</tspan><tspan class="lc-read-row" dx="4">${esc(l.label)} ` +
    `<tspan class="lc-read-v">${esc(compactMoney(l.values[i] || 0))}</tspan></tspan>`
  ).join("");
  return `<text class="lc-read ${cls}" x="${x0}" y="${yy}"><tspan class="lc-read-day">${esc(day)}</tspan>${parts}</text>`;
}

/** Multi-series line chart on ONE linear $ axis from 0, so every line's
 *  height is proportional to its dollars — never add a second axis. Values
 *  show on hover only, in a readout strip above the plot (CSS, no JS). */
export function lineChartSvg(lines: ChartLine[], labels: string[], opts: LineChartOptions = {}): string {
  const W = 960;
  const H = opts.height ?? 280;
  const readout = opts.readoutLabels;
  const pl = 62;
  const pr = opts.endLabels ? 104 : 18;
  const pt = readout ? 34 : 14;
  const pb = 30;
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

  const dots = lines.map((l) => l.values.map((v, i) =>
    `<circle class="lc-dot" cx="${x(i).toFixed(1)}" cy="${y(v || 0).toFixed(1)}" r="2" fill="${esc(l.color)}"></circle>`
  ).join("")).join("");

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
  const readY = 16;
  const rest = readout && n ? readoutText("lc-rest", pl, readY, readout[n - 1] || labels[n - 1], lines, n - 1) : "";
  const cols = labels.map((lab, i) => {
    const hit = `<rect class="lc-hit" x="${(x(i) - colW / 2).toFixed(1)}" y="${pt}" width="${colW.toFixed(1)}" height="${ih}"></rect>`;
    if (!readout) {
      const tip = [lab, ...lines.slice().sort((a, b) => (b.values[i] || 0) - (a.values[i] || 0))
        .map((l) => `${l.label}: ${money(l.values[i] || 0)}`)].join("\n");
      return hit.replace("></rect>", `><title>${esc(tip)}</title></rect>`);
    }
    const big = lines.map((l) =>
      `<circle class="lc-hov" cx="${x(i).toFixed(1)}" cy="${y(l.values[i] || 0).toFixed(1)}" r="4" fill="${esc(l.color)}"></circle>`
    ).join("");
    return `<g class="lc-col">` +
      `<line class="lc-guide lc-hov" x1="${x(i).toFixed(1)}" x2="${x(i).toFixed(1)}" y1="${pt}" y2="${base.toFixed(1)}"></line>` +
      big + readoutText("lc-hov", pl, readY, readout[i] || lab, lines, i) + hit + `</g>`;
  }).join("");

  return `<svg class="line-chart" viewBox="0 0 ${W} ${H}" data-base="${base.toFixed(1)}" role="img" aria-label="Purchase trend chart">
        ${grid}${xl}${paths}${dots}${ends}${rest}${cols}
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
