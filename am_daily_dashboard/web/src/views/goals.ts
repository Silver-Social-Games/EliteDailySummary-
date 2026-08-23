/** Elite Goals — MTD against target, weighted score out of 80 + the manager's 20.
 *
 * Numbers, pace and status all arrive precomputed from goals.py. Nothing here
 * recalculates a KPI; it only chooses tone and layout.
 */
import type { Dict } from "./../types";
import { esc, icon } from "./../format";
import { scoreLegendHtml, scoreMeterHtml } from "./../cells";
import { emptyState } from "./../components";
import { agentBlock } from "./../selectors";
import { tableHtml } from "./../table";

/** Compact Goals block for the Morning Brief. */
export function goalsSummaryCard(goals: Dict | undefined): string {
  if (!goals || !goals.available) return "";
  const score = goals.score || {};
  const pct = Number(goals.weightedTrackedPct);
  const kpis: Dict[] = goals.kpis || [];
  const onTrack = kpis.filter((k) => k.statusTone === "success").length;
  const behind = kpis.filter((k) => k.statusTone === "danger" || k.statusTone === "warning").length;
  const meterTone = pct >= 90 ? "success" : pct >= 70 ? "warning" : "danger";
  return `<div class="card gold-top">
        <div class="card-head">
          <span class="card-icon ${meterTone}">${icon("target", "ic-sm")}</span>
          <div><div class="card-title">Elite Goals</div>
          <div class="card-sub">${esc(goals.monthLabel || "")}${goals.asOf ? ` · as of ${esc(goals.asOf)}` : ""}</div></div>
          <div class="spacer"></div>
          <button type="button" class="btn" data-go="goals">Open ${icon("chev-right", "ic-xs")}</button>
        </div>
        <div class="card-body stack-10">
          <div class="goal-score">
            <span class="goal-pct t-${meterTone}">${esc(score.kpiPointsDisplay ?? score.kpiPoints ?? "—")}</span>
            <span class="t-tertiary">Personal goals progress</span>
          </div>
          ${scoreMeterHtml(score, meterTone)}
          ${scoreLegendHtml(score, meterTone)}
          <div class="row">
            <span class="badge success">${icon("check-circle", "ic-xs")}${onTrack} on track</span>
            <span class="badge ${behind ? "danger" : ""}">${icon("alert", "ic-xs")}${behind} need attention</span>
          </div>
        </div>
      </div>`;
}

export function viewGoals(): string {
  const goals = agentBlock().goals;
  if (!goals) {
    return emptyState("target", "No goals for this AM",
      "Goals are tracked for Coral, Gabriel, Lee and Rachel.");
  }
  if (!goals.available) {
    return emptyState("target", "Goals unavailable", goals.note || "No goals for this AM.");
  }
  const kpis: Dict[] = goals.kpis || [];
  const score = goals.score || {};
  const pct = Number(goals.weightedTrackedPct);
  const meterTone = pct >= 90 ? "success" : pct >= 70 ? "warning" : "danger";
  const subtitle = [
    goals.monthLabel || "",
    goals.asOf ? `as of ${goals.asOf}` : "",
    goals.elapsedDays && goals.daysInMonth ? `day ${goals.elapsedDays} of ${goals.daysInMonth}` : "",
  ].filter(Boolean).join(" · ");
  const rows = kpis.map((k) => [
    esc(k.label), esc(k.weightLabel), esc(k.goalDisplay), esc(k.actualDisplay),
    esc(k.paceDisplay), esc(k.gapDisplay),
    `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
  ]);
  return `<div class="stack">
        <div class="card">
          <div class="card-body stack-10">
            <div class="row">
              <div class="goal-score">
                <span class="goal-pct t-${meterTone}">${esc(score.kpiPointsDisplay || "—")}</span>
                <span class="t-tertiary">Personal goals progress</span>
              </div>
              <div class="spacer"></div>
              <span class="badge">${esc(subtitle)}</span>
            </div>
            ${scoreMeterHtml(score, meterTone)}
            ${scoreLegendHtml(score, meterTone)}
          </div>
        </div>
        <div class="card">
          ${tableHtml(["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"], rows,
            ["left", "right", "right", "right", "right", "right", "left"],
            kpis.map((k) => k.statusTone || "neutral"), { markerCol: 0 })}
        </div>
        <div class="note">${esc(goals.definitionsNote || "")}</div>
        <div class="note">${esc(goals.achievementCapNote || "")}</div>
      </div>`;
}
