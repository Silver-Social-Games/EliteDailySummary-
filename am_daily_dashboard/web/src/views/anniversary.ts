/** One-Month Anniversary — players who just crossed 30 days under management.
 *
 * Trigger is agent_start_managed_date + config.ANNIVERSARY_MANAGED_DAYS landing
 * in the trailing config.ANNIVERSARY_WINDOW_DAYS ending on the report date.
 * Locked, self-excluded, and TAB players are omitted upstream. Drafts are
 * review-only, gated the same way as Birthdays.
 */
import type { Dict } from "./../types";
import { esc } from "./../format";
import { aidHtml, ltpHtml, holdHtml, moneyHtml, ticketHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function sortAnniversary(rows: Dict[], mode: string): Dict[] {
  const copy = [...rows];
  if (mode === "ltpHigh")
    return copy.sort((a, b) => (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0));
  if (mode === "p7dHigh")
    return copy.sort((a, b) => (b.purchase7dNum || 0) - (a.purchase7dNum || 0));
  if (mode === "name")
    return copy.sort((a, b) => String(a.lastName || a.name).localeCompare(String(b.lastName || b.name)));
  // Default: soonest anniversary first (rows arrive already ordered by date).
  return copy;
}

export function viewAnniversary(): string {
  return tableCard({
    rows: rowsFor("anniversary"), stateKey: `anniv_${app.agent}`,
    showSearch: true, extraKeys: ["email", "firstName", "lastName"],
    forcePaginate: true, pageSize: 10,
    sortOptions: [
      { value: "date", label: "Sort: Anniversary (soonest)" },
      { value: "ltpHigh", label: "Lifetime purchase ↓" },
      { value: "p7dHigh", label: "7D purchase ↓" },
      { value: "name", label: "Name (A–Z)" },
    ],
    defaultSort: "date",
    sortFn: sortAnniversary,
    headers: ["AID", "Email", "First Name", "Last Name", "Managed Since", "Anniversary",
      "LTP", "Hold %", "7D Purchase", "Ticket"],
    align: ["left", "left", "left", "left", "left", "left", "right", "right", "right", "center"],
    markerCol: 5,
    empty: "No one-month anniversaries in the Last 3 Days.",
    renderRow: (p) => [aidHtml(p), esc(p.email), esc(p.firstName), esc(p.lastName),
      esc(p.managedDate),
      `<span class="t-success w-semibold">${esc(p.anniversaryDate)}</span>`,
      ltpHtml(p.lifetimePurchase, p.lifetimePurchasedNum), holdHtml(p.lifetimeHold),
      moneyHtml(p.purchase7d), ticketHtml(p)],
  });
}
