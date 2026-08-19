/** Birthdays · Last 3 Days — a reason to reach out.
 *
 * Window is config.BIRTHDAYS_LOOKBACK_DAYS. Drafts are review-only and are
 * refused for locked or self-excluded accounts.
 */
import { esc } from "./../format";
import { aidHtml, ticketHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewBirthdays(): string {
  return tableCard({
    rows: rowsFor("birthdays"), stateKey: `bd_${app.agent}`, showSearch: false,
    headers: ["AID", "Name", "Email", "DOB", "Age", "Ticket"],
    align: ["left", "left", "left", "left", "right", "center"], markerCol: 3,
    empty: "No birthdays in the last 3 days.",
    renderRow: (p) => [aidHtml(p), esc(p.name), esc(p.email),
      `<span class="t-success w-semibold">${esc(p.dob)}</span>`, esc(p.age ?? "—"), ticketHtml(p)],
  });
}
