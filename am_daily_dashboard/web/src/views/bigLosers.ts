/** Big Losers ≥ $5K — players whose GGR was ≥ +$5,000 (house win) in the lookback window. */
import { esc } from "./../format";
import { aidHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewBigLosers(): string {
  return tableCard({
    rows: rowsFor("bigLosers"),
    stateKey: `bl_${app.agent}`,
    showSearch: false,
    sortOptions: [{ value: "loss", label: "Sort: House win ↓" }],
    defaultSort: "loss",
    sortFn: (r) => sortByNumKey(r, "lossGgrNum", true),
    headers: ["AID", "Name", "AM", "House win (GGR)", "SC Turnover", "SC Won", "Game", "Created", "Pending RD"],
    align: ["left", "left", "left", "right", "right", "right", "left", "left", "right"],
    markerCol: 3,
    empty: "No big losers in the Last 3 Days.",
    renderRow: (p) => [
      aidHtml(p),
      esc(p.name),
      `<span class="t-small">${esc(p.agentName || app.agent)}</span>`,
      `<span class="t-danger w-semibold">${esc(p.lossGgr)}</span>`,
      `<span class="t-small">${esc(p.scTurnover)}</span>`,
      `<span class="t-small">${esc(p.scWon)}</span>`,
      `<span class="t-small t-tertiary">${esc(p.game || "—")}</span>`,
      `<span class="t-small">${esc(p.created || "—")}</span>`,
      p.pendingRdNum
        ? `<span class="t-warning w-semibold">${esc(p.pendingRd)}</span>`
        : `<span class="t-quaternary">—</span>`,
    ],
  });
}
