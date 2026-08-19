/** Open Tickets — open Zendesk tickets on this AM's book.
 *
 * TIDs always link to Zendesk. TID means Zendesk ticket ID, never a payment or
 * transaction identifier.
 */
import { esc } from "./../format";
import { aidHtml, holdHtml, moneyHtml, ticketIdsHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewTickets(): string {
  return tableCard({
    rows: rowsFor("zendesk"), stateKey: `zd_${app.agent}`, extraKeys: ["ticketIds"],
    sortOptions: [
      { value: "ltp", label: "Sort: LTP ↓" },
      { value: "tickets", label: "Sort: Open Tickets ↓" },
      { value: "purchase7d", label: "Sort: 7D Purchase ↓" },
    ],
    defaultSort: "ltp",
    sortFn: (rows, s) => s === "tickets" ? sortByNumKey(rows, "openTickets", true)
      : s === "purchase7d" ? sortByNumKey(rows, "purchase7dNum", true)
      : sortByNumKey(rows, "lifetimePurchasedNum", true),
    headers: ["AID", "Name", "LTP", "Hold", "7D Purchase", "Open Tickets", "Ticket"],
    align: ["left", "left", "right", "right", "right", "right", "left"], markerCol: 2,
    empty: "No open tickets.",
    renderRow: (p) => [aidHtml(p), esc(p.name),
      moneyHtml(p.lifetimePurchase || "$0", (p.lifetimePurchasedNum || 0) >= 50000),
      holdHtml(p.lifetimeHold || "n/a"), moneyHtml(p.purchase7d || "$0"),
      esc(p.openTickets), ticketIdsHtml(p)],
  });
}
