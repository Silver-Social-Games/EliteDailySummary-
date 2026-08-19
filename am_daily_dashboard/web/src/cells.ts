/** Single-cell renderers, shared by every section.
 *
 * These are the counterpart of canvas_parts/cells.py — a change to how an AID,
 * a TID, a WoW arrow or the score meter looks belongs here and in that file.
 */
import type { Dict } from "./types";
import { esc, icon } from "./format";

export function marker(tone?: string): string {
  return `<span class="marker marker-${tone || "neutral"}"></span>`;
}

export function markerCell(tone: string | undefined, content: string): string {
  return `<span class="cell-marker">${marker(tone)}<span>${content}</span></span>`;
}

export function wowHtml(value: unknown): string {
  const v = String(value || "").trim();
  const pct = (v.match(/\(([+-]?\d+(?:\.\d+)?)%\)/) || [])[1];
  const n = pct != null ? Number(pct) : NaN;
  const up =
    (!Number.isNaN(n) && n > 0) ||
    (v.startsWith("+") && !v.startsWith("+$0") && !v.startsWith("+0"));
  const down = (!Number.isNaN(n) && n < 0) || v.startsWith("-") || v.startsWith("$-");
  if (up) return `<span class="t-success w-semibold">${icon("trend-up", "ic-xs")} ${esc(value)}</span>`;
  if (down) return `<span class="t-danger w-semibold">${icon("trend-down", "ic-xs")} ${esc(value)}</span>`;
  return esc(value);
}

export function moneyHtml(value: unknown, emphasize?: boolean): string {
  return emphasize ? `<span class="t-danger w-semibold">${esc(value)}</span>` : esc(value);
}

export function holdHtml(value: unknown): string {
  const pct = parseFloat(value as string);
  return !Number.isNaN(pct) && pct >= 70
    ? `<span class="t-success w-semibold">${esc(value)}</span>`
    : esc(value);
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

/* Two-track score meter. The KPI track fills to kpiPoints/kpiPointsMax; the
   manager track stays dashed and empty until a score exists, because an
   unset appreciation is neither 0 nor 20. */
export function scoreMeterHtml(score: Dict, tone: string): string {
  const kpiMax = Number(score.kpiPointsMax) || 0;
  const kpiPct =
    kpiMax > 0 ? Math.max(0, Math.min(100, (Number(score.kpiPoints) / kpiMax) * 100)) : 0;
  const scored = !!score.managerScored;
  const mgrMax = Number(score.managerPointsMax) || 0;
  const mgrPct =
    scored && mgrMax > 0
      ? Math.max(0, Math.min(100, (Number(score.managerPoints) / mgrMax) * 100))
      : 0;
  return `<div class="score-meter">
        <span class="trk kpi"><span class="fill ${tone}" style="width:${kpiPct.toFixed(2)}%"></span></span>
        <span class="trk mgr${scored ? "" : " pending"}">${
          scored ? `<span class="fill mgr" style="width:${mgrPct.toFixed(2)}%"></span>` : ""
        }</span>
      </div>`;
}

export function scoreLegendHtml(score: Dict, tone: string): string {
  const scored = !!score.managerScored;
  return `<div class="score-legend">
        <span><i class="lg-${tone}"></i>KPI ${esc(score.kpiPointsDisplay || "")}</span>
        <span><i class="lg-mgr"></i>Manager ${esc(score.managerPointsDisplay || "Pending")}</span>
        ${scored && score.managerNote ? `<span class="t-tertiary">${esc(score.managerNote)}</span>` : ""}
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

export function p7dHtml(value: unknown): string {
  const none = value === "None In 7D";
  return `<span class="p7d-cell ${none ? "t-warning w-semibold" : ""}">${esc(value)}</span>`;
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
  const subj = p.ticketSubject || "";
  const preview = subj.length > 30 ? subj.slice(0, 29) + "…" : subj || "Draft";
  return (
    `<div><button type="button" class="chip" data-ticket-aid="${esc(p.aid)}">` +
    `${icon("ticket", "ic-xs")} Draft</button>` +
    `<div class="ticket-preview">${esc(preview)}</div></div>`
  );
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
