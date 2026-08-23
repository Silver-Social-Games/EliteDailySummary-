/** Big Winners ≥ $20K — players whose report-day GGR was ≤ −$20,000.
 *
 * GGR is house-side (profit − loss), so a player win is a *negative* GGR day.
 * win_ggr = −GGR = sc_won − sc_turnover; all three columns are shown so the
 * AM can read the gap directly. Read the sign backwards and this section lands
 * on the biggest losers instead.
 *
 * Non-Elite players (isElite=false) appear in every AM's tab — this is the
 * only section that reaches outside the Elite book. Those rows carry a warning
 * tone and a "Non-Elite" badge so the AM knows to treat them as a
 * portfolio-wide signal rather than their own player.
 *
 * Game = most-spun game on report_date from fact_gameplay_daily (best proxy
 * for "where the win happened" — no game-level GGR column exists).
 */
import { esc } from "./../format";
import { aidHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewBigWinners(): string {
  return tableCard({
    rows: rowsFor("bigWinners"),
    stateKey: `bw_${app.agent}`,
    showSearch: false,
    sortOptions: [{ value: "win", label: "Sort: Win ↓" }],
    defaultSort: "win",
    sortFn: (rows) => sortByNumKey(rows, "winGgrNum", true),
    headers: ["AID", "Name", "Elite / AM", "Win (GGR)", "SC Turnover", "SC Won", "Game", "Pending RD"],
    align: ["left", "left", "left", "right", "right", "right", "left", "right"],
    markerCol: 3,
    empty: "No big winners yesterday.",
    renderRow: (p) => [
      aidHtml(p),
      esc(p.name),
      p.isElite
        ? `<span class="t-small">${esc(p.agentName || "Elite")}</span>`
        : `<span class="badge warning">Non-Elite</span>`,
      `<span class="t-success w-semibold">${esc(p.winGgr)}</span>`,
      `<span class="t-small">${esc(p.scTurnover)}</span>`,
      `<span class="t-small">${esc(p.scWon)}</span>`,
      `<span class="t-small t-tertiary">${esc(p.game || "—")}</span>`,
      p.pendingRdNum
        ? `<span class="t-warning w-semibold">${esc(p.pendingRd)}</span>`
        : `<span class="t-quaternary">—</span>`,
    ],
  });
}
