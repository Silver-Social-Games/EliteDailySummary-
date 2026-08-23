/** Manager Dashboard — cross-AM roll-up. Gated; never in a per-AM file. */
import type { Dict } from "./../types";
import { AGENTS, OVERVIEW } from "./../payload";
import { esc, icon } from "./../format";
import { scoreMeterHtml } from "./../cells";
import { dailyTriggerMetrics, eliteSnapshotCards, gateHtml, metricBand, segmentHero } from "./../components";
import { app } from "./../state";
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
  return out;
}

export function viewDashboard(): string {
  if (!app.unlocked) return gateHtml();

  const focus = aggregateFocus();
  const triggerMetrics = dailyTriggerMetrics(focus);

  const scored = AGENTS
    .filter((a) => a.goals && a.goals.available)
    .map((a) => {
      const kpis: Dict[] = a.goals.kpis || [];
      const sc: Dict = a.goals.score || {};
      return {
        name: a.agentName,
        score: sc,
        pct: Number(sc.totalPctOfMax ?? a.goals.weightedTrackedPct),
        kpiPct: Number(a.goals.weightedTrackedPct),
        onTrack: kpis.filter((k) => k.statusTone === "success").length,
        behind: kpis.filter((k) => k.statusTone === "danger" || k.statusTone === "warning").length,
        total: kpis.length,
      };
    })
    .sort((a, b) => (b.pct || 0) - (a.pct || 0));

  const leaderRows = scored.map((s, i) => {
    const tone = s.kpiPct >= 90 ? "success" : s.kpiPct >= 70 ? "warning" : "danger";
    return [
      `<span class="badge ${i === 0 ? "brand" : ""}">${i + 1}</span>`,
      `<button type="button" class="chip" data-agent="${esc(s.name)}">${esc(s.name)}</button>`,
      `<span class="w-semibold t-${tone}">${esc(s.score.kpiPointsDisplay || "—")}</span>`,
      `<div style="min-width:150px">${scoreMeterHtml(s.score, tone)}</div>`,
      `<span class="t-success w-semibold">${s.onTrack}</span>`,
      `<span class="${s.behind ? "t-danger w-semibold" : "t-quaternary"}">${s.behind}</span>`,
    ];
  });

  const ovRows = OVERVIEW.map((r) => [
    `<button type="button" class="chip" data-agent="${esc(r.agentName)}">${esc(r.agentName)}</button>`,
    `<span class="t-success w-semibold">${esc(r.purchase)}</span>`,
    esc(r.purchasedOfBook || r.purchasedPlayers),
    esc(r.openZd), esc(r.takeABreak), esc(r.locked), esc(r.rdOver5k),
    `<span class="t-success">${esc(r.birthdays)}</span>`, esc(r.declineCount),
  ]);

  const leaderboard = scored.length ? `<div class="card gold-top">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Goals Leaderboard</div>
            <div class="card-sub">Personal goals progress · KPI out of 80</div></div>
          </div>
          ${tableHtml(["#", "AM", "Score", "", "On track", "Needs attention"], leaderRows,
            ["center", "left", "right", "left", "right", "right"],
            scored.map((s) => s.kpiPct >= 90 ? "success" : s.kpiPct >= 70 ? "warning" : "danger"),
            { markerCol: 1 })}
        </div>` : "";

  return `<div class="stack">
        ${segmentHero()}
        ${metricBand("Elite Snapshot", eliteSnapshotCards(), { cols: 4 })}
        ${metricBand("Daily Triggers", triggerMetrics, { subtitle: "Cross-AM roll-up · click a metric to open the section", cols: 7 })}

        <div class="grid-2">
          ${teamGoalsCard()}
          ${leaderboard}
        </div>

        <div class="card gold-top">
          <div class="card-head">
            <span class="card-icon info">${icon("list", "ic-sm")}</span>
            <div><div class="card-title">AM Overview</div>
            <div class="card-sub">Click an AM to open their board</div></div>
          </div>
          ${tableHtml(
            ["AM", "Purchase $", "Purchased Of Portfolio", "Open Tickets", "Take A Break",
             "Locked", "Pending RD", "Birthdays", "Top 20 Decline"],
            ovRows, ["left", "right", "right", "right", "right", "right", "right", "right", "right"],
            OVERVIEW.map(() => "success"), { markerCol: 1 })}
        </div>
      </div>`;
}
