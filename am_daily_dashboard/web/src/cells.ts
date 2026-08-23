/** Single-cell renderers, shared by every section.
 *
 * These are the counterpart of canvas_parts/cells.py — a change to how an AID,
 * a TID, a WoW arrow or the score meter looks belongs here and in that file.
 */
import type { Dict } from "./types";
import { esc, icon, toNum } from "./format";

/** USD / count coloring — high = green, critical low = red, else plain. */
export type NumTone = "high" | "low" | "neutral";

const LTP_HIGH_USD = 50_000;
const PURCHASE_HIGH_USD = 10_000;
const HOLD_HIGH_PCT = 70;
const HOLD_LOW_PCT = 30;

function numToneSpan(value: unknown, tone: NumTone): string {
  if (tone === "neutral") return esc(value);
  const cls = tone === "high" ? "t-success" : "t-danger";
  return `<span class="${cls} w-semibold">${esc(value)}</span>`;
}

export function marker(tone?: string): string {
  return `<span class="marker marker-${tone || "neutral"}"></span>`;
}

export function markerCell(tone: string | undefined, content: string): string {
  return `<span class="cell-marker">${marker(tone)}<span>${content}</span></span>`;
}

function wowTone(value: unknown): "success" | "danger" | "neutral" {
  const v = String(value || "").trim();
  const pct = (v.match(/\(([+-]?\d+(?:\.\d+)?)%\)/) || [])[1]
    ?? (v.match(/^([+-]?\d+(?:\.\d+)?)%$/) || [])[1];
  const n = pct != null ? Number(pct) : NaN;
  if (!Number.isNaN(n)) {
    if (n > 0) return "success";
    if (n < 0) return "danger";
    return "neutral";
  }
  if (v.startsWith("+") && !v.startsWith("+$0") && !v.startsWith("+0")) return "success";
  if (v.startsWith("-") || v.startsWith("$-")) return "danger";
  return "neutral";
}

/** Compact pill for segment KPI rows. */
export function wowPillHtml(value: unknown): string {
  const v = String(value || "").trim();
  if (!v || v === "—") return `<span class="wow-pill neutral">—</span>`;
  const tone = wowTone(v);
  const label = v.replace(/^\(([+-]?\d+(?:\.\d+)?)%\)\s*/, "").trim() || v;
  const arrow = tone === "success" ? "▲" : tone === "danger" ? "▼" : "";
  const text = arrow ? `${label} ${arrow}` : label;
  return `<span class="wow-pill ${tone}">${esc(text)}</span>`;
}

export function wowHtml(value: unknown): string {
  const v = String(value || "").trim();
  const tone = wowTone(v);
  if (tone === "success") return `<span class="t-success w-semibold">${icon("trend-up", "ic-xs")} ${esc(value)}</span>`;
  if (tone === "danger") return `<span class="t-danger w-semibold">${icon("trend-down", "ic-xs")} ${esc(value)}</span>`;
  return esc(value);
}

export function moneyHtml(value: unknown, tone: NumTone = "neutral"): string {
  return numToneSpan(value, tone);
}

/** Lifetime purchase — high LTP green, zero red. */
export function ltpHtml(value: unknown, num?: number): string {
  const n = num ?? toNum(value);
  if (n >= LTP_HIGH_USD) return numToneSpan(value, "high");
  if (n <= 0) return numToneSpan(value, "low");
  return esc(value);
}

/** Day / 7D purchase amounts — big green, zero or missing red. */
export function purchaseMoneyHtml(value: unknown, num?: number): string {
  const v = String(value ?? "").trim();
  if (!v || v === "—" || v === "$0") return numToneSpan(value, "low");
  const n = num ?? toNum(value);
  if (n >= PURCHASE_HIGH_USD) return numToneSpan(value, "high");
  if (n <= 0) return numToneSpan(value, "low");
  return esc(value);
}

export function holdHtml(value: unknown): string {
  const v = String(value ?? "").trim();
  if (!v || v === "—" || v.toLowerCase() === "n/a") return esc(value);
  const pct = parseFloat(v);
  if (Number.isNaN(pct)) return esc(value);
  if (pct >= HOLD_HIGH_PCT) return numToneSpan(value, "high");
  if (pct <= HOLD_LOW_PCT) return numToneSpan(value, "low");
  return esc(value);
}

export function unlockHtml(detail: unknown, remainingDays: unknown): string {
  if (!detail) return '<span class="t-quaternary">—</span>';
  const urgent = typeof remainingDays === "number" && remainingDays <= 0;
  return urgent
    ? `<span class="t-danger w-semibold">${icon("alert", "ic-xs")} ${esc(detail)}</span>`
    : esc(detail);
}

export function agingHtml(created: unknown, daysPending: unknown, agingFlag: unknown): string {
  const suffix = typeof daysPending === "number" ? ` (${daysPending}d ago)` : "";
  return agingFlag
    ? `<span class="t-small t-danger w-semibold">${icon("clock", "ic-xs")} ${esc(created)}${esc(suffix)}</span>`
    : `<span class="t-small">${esc(created)}${esc(suffix)}</span>`;
}

/* KPI-only score meter (out of 80). Manager appreciation stays off the AM view. */
export function scoreMeterHtml(score: Dict, tone: string): string {
  const kpiMax = Number(score.kpiPointsMax) || 80;
  const kpiPct =
    kpiMax > 0 ? Math.max(0, Math.min(100, (Number(score.kpiPoints) / kpiMax) * 100)) : 0;
  return `<div class="score-meter single">
        <span class="trk kpi"><span class="fill ${tone}" style="width:${kpiPct.toFixed(2)}%"></span></span>
      </div>`;
}

export function scoreLegendHtml(score: Dict, tone: string): string {
  return `<div class="score-legend">
        <span><i class="lg-${tone}"></i>${esc(score.kpiPointsDisplay || "")} · Personal goals progress</span>
      </div>`;
}

export function bigWinHtml(p: Dict): string {
  const won = p.wonYesterday || "—";
  return p.bigWinner
    ? `<span class="t-small t-danger w-semibold">${icon("trend-up", "ic-xs")} ${esc(won)} · Big Winner</span>`
    : `<span class="t-small t-tertiary">${esc(won)}</span>`;
}

/* Blank when nothing is flagged. No missing-document ticket is not proof the
   documents are complete, so this stays silent rather than showing an
   all-clear an AM might repeat to a player awaiting a withdrawal. */
export function docsHtml(status: unknown): string {
  if (!status) return `<span class="t-quaternary">—</span>`;
  return `<span class="t-small t-warning w-semibold">${esc(status)}</span>`;
}

export function p7dHtml(value: unknown, num?: number): string {
  const v = String(value ?? "").trim();
  if (v === "None In 7D" || v === "—" || (num ?? toNum(value)) <= 0) {
    return `<span class="p7d-cell t-danger w-semibold">${esc(value)}</span>`;
  }
  return `<span class="p7d-cell">${esc(value)}</span>`;
}

export function urgencyHtml(u: unknown): string {
  if (u === "Today") return `<span class="badge danger">${icon("zap", "ic-xs")}Today</span>`;
  if (u === "48h") return `<span class="badge warning">48h</span>`;
  if (u === "Watch") return `<span class="badge info">Watch</span>`;
  return `<span class="t-quaternary">${esc(u || "—")}</span>`;
}

/** AID always links to Looker — every section, no exceptions. */
export function aidHtml(p: Dict): string {
  const aid = esc(p.aid);
  return p.aidUrl
    ? `<a href="${esc(p.aidUrl)}" target="_blank" rel="noopener noreferrer">${aid}</a>`
    : aid;
}

/** Draft button, or the lock label for an account no draft may be offered for. */
export function ticketHtml(p: Dict): string {
  if (!p.ticketEnabled) {
    return p.ticketDisabledReason
      ? `<span class="badge">${icon("lock", "ic-xs")}${esc(p.ticketDisabledReason)}</span>`
      : '<span class="t-quaternary">—</span>';
  }
  return `<button type="button" class="chip ticket-chip" data-ticket-aid="${esc(p.aid)}">${icon("ticket", "ic-xs")} Draft</button>`;
}

/** TIDs always link to Zendesk. */
export function ticketIdsHtml(p: Dict): string {
  const list: Dict[] = p.tickets || [];
  if (!list.length) return `<span class="t-quaternary">${esc(p.ticketIds || "—")}</span>`;
  return list
    .map(
      (t, i) =>
        `${i ? ", " : ""}<a href="${esc(t.url)}" target="_blank" rel="noopener noreferrer">${esc(t.id)}</a>`
    )
    .join("");
}
