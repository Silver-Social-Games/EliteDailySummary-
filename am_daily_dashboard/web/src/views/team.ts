/** Team Goals — manager-only, and the targets are given, never derived.
 *
 * The seven targets are `team` rows in data/elite_goals.tsv. They are NOT a sum
 * of the four AMs' targets ("my team goals are not an add up of my employees"),
 * and progress is measured over the whole managed book, Alon included.
 *
 * Deliberately has no 80 + 20 score meter: the manager's 20 points are an award
 * they make to an AM, and there is nobody to award the team's, so the KPI table
 * stands on its own. A per-AM breakdown was built, shown and dropped too — the
 * Goals Leaderboard on the Dashboard already covers it.
 */
import type { Dict } from "./../types";
import { TEAM_GOALS } from "./../payload";
import { esc, icon } from "./../format";
import { emptyState, eliteSnapshotCards, gateHtml, metricBand } from "./../components";
import { app } from "./../state";
import { tableHtml } from "./../table";

export function teamKpi(key: string): Dict | null {
  return (TEAM_GOALS && (TEAM_GOALS.kpis || []).find((k: Dict) => k.key === key)) || null;
}

/** Headline three KPIs as a card on the Manager Dashboard. */
export function teamGoalsCard(): string {
  if (!TEAM_GOALS || !TEAM_GOALS.available) return "";
  const kpis: Dict[] = TEAM_GOALS.kpis || [];
  const onTrack = kpis.filter((k) => k.statusTone === "success").length;
  const behind = kpis.filter((k) => k.statusTone === "danger" || k.statusTone === "warning").length;
  const headline = ["daily_avg_purchase", "daily_avg_net_purchase", "monthly_purchasers"]
    .map(teamKpi).filter(Boolean) as Dict[];
  return `<div class="card gold-top">
        <div class="card-head">
          <span class="card-icon ${behind ? "warning" : "success"}">${icon("target", "ic-sm")}</span>
          <div><div class="card-title">Team Goals</div>
          <div class="card-sub">Your targets, Elite Portfolio · ${esc(TEAM_GOALS.monthLabel || "")}</div></div>
          <div class="spacer"></div>
          <button type="button" class="btn" data-go="team">Open ${icon("chev-right", "ic-xs")}</button>
        </div>
        <div class="card-body stack-10">
          ${tableHtml(["KPI", "Goal", "Pace", "Status"],
            headline.map((k) => [
              esc(k.label), esc(k.goalDisplay), esc(k.paceDisplay),
              `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
            ]),
            ["left", "right", "right", "left"],
            headline.map((k) => k.statusTone || "neutral"), { markerCol: 0 })}
          <div class="row">
            <span class="badge success">${icon("check-circle", "ic-xs")}${onTrack} on track</span>
            <span class="badge ${behind ? "danger" : ""}">${icon("alert", "ic-xs")}${behind} need attention</span>
          </div>
        </div>
      </div>`;
}

export function viewTeamGoals(): string {
  if (!app.unlocked) return gateHtml();
  if (!TEAM_GOALS) {
    return emptyState("target", "No team goals in this brief",
      "Add a team row for this month to data/elite_goals.tsv and re-run the generator.");
  }
  if (!TEAM_GOALS.available) {
    return emptyState("target", "Team goals unavailable",
      TEAM_GOALS.note || "No team target row for this month.");
  }
  const g = TEAM_GOALS;
  const kpis: Dict[] = g.kpis || [];
  const subtitle = [
    g.monthLabel || "",
    g.asOf ? `as of ${g.asOf}` : "",
    g.elapsedDays && g.daysInMonth ? `day ${g.elapsedDays} of ${g.daysInMonth}` : "",
  ].filter(Boolean).join(" · ");

  const cards = eliteSnapshotCards();

  const rows = kpis.map((k) => [
    esc(k.label), esc(k.weightLabel), esc(k.goalDisplay), esc(k.actualDisplay),
    esc(k.paceDisplay), esc(k.gapDisplay),
    `<span class="badge ${k.statusTone || ""}">${esc(k.status)}</span>`,
  ]);

  /* No per-AM breakdown here, by the user's decision: these are their own
     goals, not a roll-up of their employees', and the Goals Leaderboard on
     the Dashboard already covers who contributed what. */
  return `<div class="stack">
        <div class="card gold-top">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Elite Goals · Team</div>
            <div class="card-sub">Your targets, Elite Portfolio · ${esc(g.monthLabel || "")}</div></div>
            <div class="spacer"></div>
            <span class="badge">${esc(subtitle)}</span>
          </div>
        </div>
        ${metricBand("Elite Snapshot", cards, { cols: 4 })}
        <div class="card gold-top">
          ${tableHtml(["KPI", "Weight", "Goal", "Actual", "Pace", "Gap", "Status"], rows,
            ["left", "right", "right", "right", "right", "right", "left"],
            kpis.map((k) => k.statusTone || "neutral"), { markerCol: 0 })}
        </div>
        <div class="note">These are your own targets, loaded as given, never derived
          from the AMs' targets. Progress is measured over the whole managed book,
          Alon's portfolio included: Purchasers, Reactivation and % Active are counted
          as distinct accounts across the book, and ARPPU and % Active are rebuilt from
          the book totals rather than averaged across the AMs.</div>
        <div class="note">${esc(g.definitionsNote || "")}</div>
        <div class="note">${esc(g.achievementCapNote || "")}</div>
      </div>`;
}
