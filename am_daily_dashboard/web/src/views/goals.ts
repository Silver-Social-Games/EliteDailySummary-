/** Elite Goals — MTD against target, KPI score out of 80 (+ manager 20 tracked separately).
 *
 * Numbers, pace and status all arrive precomputed from goals.py. Nothing here
 * recalculates a KPI; it only chooses tone and layout.
 */
import type { Dict } from "./../types";
import { esc, icon } from "./../format";
import { scoreMeterHtml, goalsScoreTone, amScoreDisplay } from "./../cells";
import { emptyState, goalsHistoryCard } from "./../components";
import { agentBlock } from "./../selectors";
import { tableHtml } from "./../table";

function amScoreTone(goals: Dict): string {
  return goalsScoreTone(goals);
}

/** Compact Goals block for the Morning Brief. */
export function goalsSummaryCard(goals: Dict | undefined): string {
  if (!goals || !goals.available) return "";
  const score = goals.score || {};
  const meterTone = amScoreTone(goals);
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
            <span class="goal-pct t-${meterTone}">${esc(amScoreDisplay(goals))}</span>
          </div>
          ${scoreMeterHtml(score, meterTone)}
        </div>
      </div>`;
}

export function viewGoals(): string {
  const agent = agentBlock();
  const goals = agent.goals;
  if (!goals) {
    return emptyState("target", "No goals for this AM",
      "Goals are tracked for Coral, Gabriel, Lee and Rachel.");
  }
  if (!goals.available) {
    return emptyState("target", "Goals unavailable", goals.note || "No goals for this AM.");
  }
  const kpis: Dict[] = goals.kpis || [];
  const score = goals.score || {};
  const meterTone = amScoreTone(goals);
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
                <span class="goal-pct t-${meterTone}">${esc(amScoreDisplay(goals))}</span>
              </div>
              <div class="spacer"></div>
              <span class="badge">${esc(subtitle)}</span>
            </div>
            ${scoreMeterHtml(score, meterTone)}
          </div>
        </div>
        <div class="card">
          ${tableHtml(["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"], rows,
            ["left", "right", "right", "right", "right", "right", "left"],
            kpis.map((k) => k.statusTone || "neutral"), { markerCol: 0 })}
        </div>
        ${goalsHistoryCard(goals.history)}
      </div>`;
}
