/** Pending Redemptions — locked withdrawals at or above the threshold.
 *
 * Thresholds live in config.py, never inline. Won Yesterday flips the
 * house-side GGR sign (a player win is a negative GGR day) and shows an em dash
 * on a losing day rather than a negative win.
 */
import { esc } from "./../format";
import { agingHtml, aidHtml, bigWinHtml, docsHtml, holdHtml, ltpHtml, purchaseMoneyHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewPendingRd(): string {
  return tableCard({
    rows: rowsFor("rdOver5k"), stateKey: `rd5_${app.agent}`, showSearch: false,
    sortOptions: [
      { value: "amount", label: "Sort: Amount ↓" },
      { value: "won", label: "Sort: Won Yesterday ↓" },
      { value: "oldest", label: "Sort: Oldest first" },
    ],
    defaultSort: "amount",
    sortFn: (rows, s) => s === "oldest" ? sortByNumKey(rows, "daysPending", true)
      : s === "won" ? sortByNumKey(rows, "wonYesterdayNum", true)
      : sortByNumKey(rows, "amountNum", true),
    headers: ["AID", "Name", "RD ID", "Amount", "Status", "Created", "Won Yesterday", "Docs", "LTP", "Hold", "7D Purchase"],
    align: ["left", "left", "left", "right", "left", "left", "right", "left", "right", "right", "right"], markerCol: 3,
    empty: "No pending redemptions.",
    renderRow: (p) => [aidHtml(p), esc(p.name), esc(p.redeemId),
      `<span class="t-warning w-semibold">${esc(p.amount)}</span>`, esc(p.status),
      agingHtml(p.created, p.daysPending, p.agingFlag),
      bigWinHtml(p), docsHtml(p.docsStatus),
      ltpHtml(p.lifetimePurchase || "—", p.lifetimePurchasedNum),
      holdHtml(p.lifetimeHold || "—"),
      purchaseMoneyHtml(p.purchase7d || "—", p.purchase7dNum)],
  });
}
