/** Responsiveness · 90-day silent book — players an AM has not heard from.
 *
 * Players whose most recent Zendesk ticket activity (created or updated) is
 * older than config.TICKET_INACTIVITY_DAYS (90). The selection is made
 * upstream in ticket_inactivity_sql; accounts that never opened a ticket are
 * not surfaced, so this is a re-engagement prompt for players who were once in
 * contact and have gone quiet. Locked, self-excluded, and TAB players are
 * omitted upstream (elite-core outreach rule).
 */
import type { Dict } from "./../types";
import { esc } from "./../format";
import { aidHtml, ltpHtml, holdHtml, purchaseMoneyHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function sortResponsiveness(rows: Dict[], mode: string): Dict[] {
  const copy = [...rows];
  if (mode === "ltpHigh")
    return copy.sort((a, b) => (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0));
  if (mode === "holdHigh")
    return copy.sort((a, b) => (b.holdPctNum || 0) - (a.holdPctNum || 0));
  if (mode === "name")
    return copy.sort((a, b) => String(a.lastName || a.name).localeCompare(String(b.lastName || b.name)));
  // Default: longest silent first (rows arrive already ordered by days).
  return copy;
}

export function viewResponsiveness(): string {
  return tableCard({
    rows: rowsFor("responsiveness"), stateKey: `resp_${app.agent}`,
    pagerNote: "No support ticket activity in 90+ days",
    showSearch: true, extraKeys: ["email", "firstName", "lastName"],
    forcePaginate: true, pageSize: 10,
    sortOptions: [
      { value: "silentHigh", label: "Sort: Days Silent ↓" },
      { value: "ltpHigh", label: "Lifetime purchase ↓" },
      { value: "holdHigh", label: "Hold % ↓" },
      { value: "name", label: "Name (A–Z)" },
    ],
    defaultSort: "silentHigh",
    sortFn: sortResponsiveness,
    headers: ["AID", "Email", "First Name", "Last Name", "Last Contact", "Days Silent",
      "Hold %", "30D Purchase", "LTP"],
    align: ["left", "left", "left", "left", "left", "right", "right", "right", "right"],
    markerCol: 0,
    empty: "No silent players. Everyone has had a support ticket within 90 days.",
    renderRow: (p) => [aidHtml(p), esc(p.email), esc(p.firstName), esc(p.lastName),
      esc(p.lastContact || "—"),
      `<span class="w-semibold">${esc(p.daysSinceTicket ?? "—")}${p.daysSinceTicket != null ? "d" : ""}</span>`,
      holdHtml(p.holdPct), purchaseMoneyHtml(p.purchase30d, p.purchase30dNum),
      ltpHtml(p.lifetimePurchase, p.lifetimePurchasedNum)],
  });
}
