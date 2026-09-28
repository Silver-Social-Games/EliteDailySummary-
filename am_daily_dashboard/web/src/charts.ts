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
  /** Right axis carries a series on a different scale (Jackpota vs a book). */
  axis?: "left" | "right";
  width?: number;
  dashed?: boolean;
}

function niceMax(v: number): number {
  if (!(v > 0)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const m = v / p;
  const nice = m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10;
  return nice * p;
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

/** Multi-series line chart with a $ left axis, optional right axis, and one
 *  hover column per point whose native tooltip lists every series. */
export function lineChartSvg(lines: ChartLine[], labels: string[], height = 340): string {
  const W = 960;
  const H = height;
  const hasRight = lines.some((l) => l.axis === "right");
  const pl = 62, pr = hasRight ? 62 : 18, pt = 14, pb = 30;
  const iw = W - pl - pr;
  const ih = H - pt - pb;
  const n = labels.length;
  const x = (i: number) => pl + (n <= 1 ? iw / 2 : (i * iw) / (n - 1));
  const axisMax = (axis: "left" | "right") =>
    niceMax(Math.max(0, ...lines.filter((l) => (l.axis || "left") === axis).flatMap((l) => l.values)));
  const lMax = axisMax("left");
  const rMax = axisMax("right");
  const yFor = (max: number) => (v: number) => pt + ih - (max > 0 ? (v / max) * ih : 0);

  let grid = "";
  for (let k = 0; k <= 4; k++) {
    const yy = pt + ih - (k / 4) * ih;
    grid += `<line class="lc-grid" x1="${pl}" x2="${W - pr}" y1="${yy}" y2="${yy}"></line>`;
    grid += `<text class="lc-axis" x="${pl - 8}" y="${yy + 4}" text-anchor="end">${esc(compactMoney((lMax * k) / 4))}</text>`;
    if (hasRight) {
      grid += `<text class="lc-axis" x="${W - pr + 8}" y="${yy + 4}" text-anchor="start">${esc(compactMoney((rMax * k) / 4))}</text>`;
    }
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
    const y = yFor(l.axis === "right" ? rMax : lMax);
    const lastI = l.values.length - 1;
    return `<path d="${pathD(l.values, x, y)}" ${lineAttrs(l, 2)}></path>` +
      `<circle cx="${x(lastI)}" cy="${y(l.values[lastI])}" r="3.5" fill="${esc(l.color)}"></circle>`;
  }).join("");

  const colW = n > 1 ? iw / (n - 1) : iw;
  const hits = labels.map((lab, i) => {
    const tip = [lab, ...lines.map((l) => `${l.label}: ${money(l.values[i] || 0)}`)].join("\n");
    return `<rect class="lc-hit" x="${(x(i) - colW / 2).toFixed(1)}" y="${pt}" width="${colW.toFixed(1)}" height="${ih}">` +
      `<title>${esc(tip)}</title></rect>`;
  }).join("");

  return `<svg class="line-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Purchase trend chart">
        ${grid}${xl}${paths}${hits}
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
