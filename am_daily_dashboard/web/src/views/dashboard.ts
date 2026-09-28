/** Manager Dashboard — cross-AM roll-up. Gated; never in a per-AM file. */
import type { Dict } from "./../types";
import { AGENTS } from "./../payload";
import { esc, icon } from "./../format";
import { scoreMeterHtml, goalsKpiPoints, goalsScoreTone, amScoreDisplay } from "./../cells";
import { dailyTriggerMetrics, eliteSnapshotCards, gateHtml, metricBand, segmentHero } from "./../components";
import { app } from "./../state";
import { uniqueBigWinnersCount } from "./../selectors";
import { tableHtml } from "./../table";
import { teamGoalsCard } from "./team";

function aggregateFocus(): Dict {
  const out: Dict = {};
  for (const a of AGENTS) {
    const f: Dict = a.focus || {};
    for (const [k, v] of Object.entries(f)) {
      out[k] = (Number(out[k]) || 0) + Number(v || 0);
    }
  }
  // Non-Elite rows are duplicated on every AM tab; count unique players instead.
  out.bigWinners = uniqueBigWinnersCount();
  return out;
}

export function viewDashboard(): string {
  if (!app.unlocked) return gateHtml();

  const focus = aggregateFocus();
  const triggerMetrics = dailyTriggerMetrics(focus);

  const scored = AGENTS
    .filter((a) => a.goals && a.goals.available)
    .map((a) => {
      const sc: Dict = a.goals.score || {};
      const { points, max } = goalsKpiPoints(a.goals);
      return {
        name: a.agentName,
        score: sc,
        scoreDisplay: amScoreDisplay(a.goals),
        kpiPoints: points,
        kpiMax: max,
      };
    })
    .sort((a, b) => (b.kpiPoints || 0) - (a.kpiPoints || 0));

  const leaderRows = scored.map((s, i) => {
    const tone = goalsScoreTone({ score: s.score, kpiPoints: s.kpiPoints, kpiPointsMax: s.kpiMax });
    return [
      `<span class="badge ${i === 0 ? "brand" : ""}">${i + 1}</span>`,
      `<button type="button" class="chip" data-agent="${esc(s.name)}">${esc(s.name)}</button>`,
      `<span class="w-semibold t-${tone}">${esc(s.scoreDisplay)}</span>`,
      `<div style="min-width:150px">${scoreMeterHtml(s.score, tone)}</div>`,
    ];
  });

  const leaderboard = scored.length ? `<div class="card gold-top goals-leaderboard">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Goals Leaderboard</div></div>
          </div>
          ${tableHtml(["#", "AM", "Score", ""], leaderRows,
            ["center", "left", "right", "left"],
            scored.map((s) => goalsScoreTone({ score: s.score, kpiPoints: s.kpiPoints, kpiPointsMax: s.kpiMax })),
            { markerCol: 1 })}
        </div>` : "";

  return `<div class="stack">
        ${segmentHero()}
        ${metricBand("Elite Snapshot", eliteSnapshotCards(), { cols: 3 })}
        ${metricBand("Daily Triggers", triggerMetrics, { subtitle: "Cross-AM roll-up · click a metric to open the section", cols: 7 })}

        <div class="grid-2 goals-pair">
          ${teamGoalsCard()}
          ${leaderboard}
        </div>
      </div>`;
}
