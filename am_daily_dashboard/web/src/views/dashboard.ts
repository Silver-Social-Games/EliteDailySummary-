/** Manager Dashboard — cross-AM roll-up. Gated; never in a per-AM file.
 *
 * The Goals Leaderboard ranks on `totalPctOfMax`, not raw points: a scored AM
 * is out of 100 and an unscored one out of 80, so ranking by point total would
 * sort every unscored AM last by default. Settled with the user, mixed
 * scored/unscored states included.
 */
import type { Dict } from "./../types";
import { AGENTS, AM_SHARES, OVERVIEW, REPORT, dayShort } from "./../payload";
import { compactMoney, esc, icon, money, richText, toNum } from "./../format";
import { scoreMeterHtml } from "./../cells";
import { gateHtml, segmentCard, statCard } from "./../components";
import { app } from "./../state";
import { tableHtml } from "./../table";
import { teamGoalsCard } from "./team";

export function viewDashboard(): string {
  if (!app.unlocked) return gateHtml();

  const purchase = AM_SHARES.reduce((s, r) => s + toNum(r.purchase), 0);
  const purchasedPlayers = AM_SHARES.reduce((s, r) => s + (Number(r.purchasedPlayers) || 0), 0);
  const book = AM_SHARES.reduce((s, r) => s + (Number(r.totalPlayers) || 0), 0);
  const sum = (k: string) => OVERVIEW.reduce((s, r) => s + (Number(r[k]) || 0), 0);
  const openZd = sum("openZd"), rd = sum("rdOver5k"), locked = sum("locked");
  const decline = sum("declineCount"), birthdays = sum("birthdays");
  const rate = book ? (purchasedPlayers / book) * 100 : 0;

  const cards = [
    { label: `Elite Purchase · ${dayShort}`, value: compactMoney(purchase), icon: "dollar", tone: "success",
      foot: `${money(purchase)} across ${AM_SHARES.length} AMs` },
    { label: "Purchased Players", value: purchasedPlayers.toLocaleString(), icon: "users", tone: "brand",
      foot: `${rate.toFixed(1)}% of the book` },
    { label: "Book Size", value: book.toLocaleString(), icon: "list", tone: "neutral",
      foot: "Tagged Elite accounts" },
    { label: "Open Tickets", value: openZd.toLocaleString(), icon: "ticket", tone: openZd ? "info" : "success" },
    { label: "Pending RD", value: rd.toLocaleString(), icon: "banknote", tone: rd ? "warning" : "success" },
    { label: "Locked", value: locked.toLocaleString(), icon: "lock", tone: locked ? "warning" : "success" },
    { label: "Top 20 Decline", value: decline.toLocaleString(), icon: "trend-down", tone: decline ? "warning" : "success" },
    { label: "Birthdays (3d)", value: birthdays.toLocaleString(), icon: "gift", tone: "brand" },
  ];

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
      `<span class="w-semibold t-${tone}">${esc(s.score.totalDisplay || "—")}</span>`,
      `<div style="min-width:150px">${scoreMeterHtml(s.score, tone)}</div>`,
      s.score.managerScored
        ? `<span class="t-manager w-semibold">${esc(s.score.managerPointsDisplay)}</span>`
        : `<span class="t-quaternary">Pending</span>`,
      `<span class="t-success w-semibold">${s.onTrack}</span>`,
      `<span class="${s.behind ? "t-danger w-semibold" : "t-quaternary"}">${s.behind}</span>`,
    ];
  });

  const shareRows = AM_SHARES.map((r) => [
    `<button type="button" class="chip" data-agent="${esc(r.agentName)}">${esc(r.agentName)}</button>`,
    `<span class="t-success w-semibold">${esc(r.purchase)}</span>`,
    esc(r.purchaseShare),
    esc(r.purchasedOfBook || r.purchasedPlayers),
  ]);

  const ovRows = OVERVIEW.map((r) => [
    `<button type="button" class="chip" data-agent="${esc(r.agentName)}">${esc(r.agentName)}</button>`,
    `<span class="t-success w-semibold">${esc(r.purchase)}</span>`,
    esc(r.purchasedOfBook || r.purchasedPlayers),
    esc(r.openZd), esc(r.takeABreak), esc(r.locked), esc(r.rdOver5k),
    `<span class="t-success">${esc(r.birthdays)}</span>`, esc(r.declineCount),
  ]);

  const greet = (REPORT.overviewGreetingLines || []).map((line: string, i: number) => richText(line, i === 0)).join("");

  return `<div class="stack">
        ${greet ? `<div class="hero"><div class="stack-6">${greet}</div></div>` : ""}
        <div class="stats">${cards.map(statCard).join("")}</div>

        ${teamGoalsCard()}

        ${scored.length ? `<div class="card">
          <div class="card-head">
            <span class="card-icon">${icon("target", "ic-sm")}</span>
            <div><div class="card-title">Goals Leaderboard</div>
            <div class="card-sub">80 KPI points + your 20 of appreciation · ranked on share of the applicable maximum</div></div>
          </div>
          ${tableHtml(["#", "AM", "Score", "", "Manager", "On track", "Needs attention"], leaderRows,
            ["center", "left", "right", "left", "right", "right", "right"],
            scored.map((s) => s.kpiPct >= 90 ? "success" : s.kpiPct >= 70 ? "warning" : "danger"),
            { markerCol: 1 })}
        </div>` : ""}

        <div class="grid-2">
          <div class="card">
            <div class="card-head">
              <span class="card-icon success">${icon("pie", "ic-sm")}</span>
              <div class="card-title">AM Share Of Elite</div>
            </div>
            ${tableHtml(["AM", "Purchase $", "Share", "Purchased Of Portfolio"], shareRows,
              ["left", "right", "right", "right"], AM_SHARES.map(() => "success"), { markerCol: 1 })}
          </div>
          ${segmentCard()}
        </div>

        <div class="card">
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
