/** Big Losers ≥ $5K — players whose report-day GGR was ≥ +$5,000 (house win). */
import { esc } from "./../format";
import { aidHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

const demoRows = (): Record<string, unknown>[] => [{
  aid: "000000000",
  name: "Sample · layout only",
  isElite: true,
  agentName: app.agent,
  lossGgr: "$8.2K",
  lossGgrNum: 8200,
  scTurnover: "$12K",
  scWon: "$3.8K",
  game: "Sample Game",
  pendingRd: "—",
  pendingRdNum: 0,
  demo: true,
}];

export function viewBigLosers(): string {
  const live = rowsFor("bigLosers");
  const demo = live.length === 0;
  const rows = demo ? demoRows() : live;
  const banner = demo
    ? `<div class="note">No player lost ≥ $5K to the house on the report date. Sample row below shows the layout.</div>`
    : "";
  return `${banner}${tableCard({
    rows,
    stateKey: `bl_${app.agent}`,
    showSearch: false,
    sortOptions: [{ value: "loss", label: "Sort: House win ↓" }],
    defaultSort: "loss",
    sortFn: (r) => sortByNumKey(r, "lossGgrNum", true),
    headers: ["AID", "Name", "AM", "House win (GGR)", "SC Turnover", "SC Won", "Game", "Pending RD"],
    align: ["left", "left", "left", "right", "right", "right", "left", "right"],
    markerCol: 3,
    empty: "No big losers yesterday.",
    renderRow: (p) => [
      p.demo ? `<span class="t-quaternary">${esc(p.aid)}</span>` : aidHtml(p),
      p.demo ? `<span class="badge neutral-soft">Sample</span> ${esc(p.name)}` : esc(p.name),
      `<span class="t-small">${esc(p.agentName || app.agent)}</span>`,
      `<span class="t-danger w-semibold">${esc(p.lossGgr)}</span>`,
      `<span class="t-small">${esc(p.scTurnover)}</span>`,
      `<span class="t-small">${esc(p.scWon)}</span>`,
      `<span class="t-small t-tertiary">${esc(p.game || "—")}</span>`,
      p.pendingRdNum
        ? `<span class="t-warning w-semibold">${esc(p.pendingRd)}</span>`
        : `<span class="t-quaternary">—</span>`,
    ],
  })}`;
}
