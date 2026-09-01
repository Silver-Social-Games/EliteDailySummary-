/** First-Time Locked RD — a player's first-ever redemption, under review.
 *
 * Rows are built by the same Python build_rd_section as Pending Redemptions,
 * with no ageing threshold, so a change to that builder hits both sections.
 */
import { esc } from "./../format";
import { aidHtml, ticketHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewFirstRd(): string {
  return tableCard({
    rows: rowsFor("rdFirstTime"), stateKey: `rdf_${app.agent}`, showSearch: false,
    headers: ["AID", "Name", "RD ID", "Amount", "Status", "Created", "Ticket"],
    align: ["left", "left", "left", "right", "left", "left", "center"], markerCol: 3,
    empty: "No first-time redemptions in the Last 3 Days.",
    renderRow: (p) => [aidHtml(p), esc(p.name), esc(p.redeemId),
      `<span class="t-warning w-semibold">${esc(p.amount)}</span>`, esc(p.status),
      esc(p.created), ticketHtml(p)],
  });
}
