/** Birthdays · Last 3 Days — a reason to reach out.
 *
 * Window is config.BIRTHDAYS_LOOKBACK_DAYS. Locked, self-excluded, and TAB
 * players are omitted upstream. Drafts are review-only.
 */
import type { Dict } from "./../types";
import { esc, icon } from "./../format";
import { aidHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function birthdayTicketHtml(p: Dict): string {
  if (!p.ticketEnabled) {
    return p.ticketDisabledReason
      ? `<span class="badge">${icon("lock", "ic-xs")}${esc(p.ticketDisabledReason)}</span>`
      : '<span class="t-quaternary">—</span>';
  }
  return `<button type="button" class="chip" data-ticket-aid="${esc(p.aid)}">${icon("ticket", "ic-xs")} Draft</button>`;
}

export function viewBirthdays(): string {
  return tableCard({
    rows: rowsFor("birthdays"), stateKey: `bd_${app.agent}`, showSearch: false,
    headers: ["AID", "Name", "Email", "DOB", "Age", "Ticket"],
    align: ["left", "left", "left", "left", "right", "center"], markerCol: 3,
    empty: "No birthdays in the Last 3 Days.",
    renderRow: (p) => [aidHtml(p), esc(p.name), esc(p.email),
      `<span class="t-success w-semibold">${esc(p.dob)}</span>`, esc(p.age ?? "—"), birthdayTicketHtml(p)],
  });
}
