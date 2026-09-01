/** Birthday Gift · Eligible — this month's birthday players who earned a gift.
 *
 * Players whose birthday falls in the current calendar month AND who meet the
 * gift criteria (lifetime Hold % >= config.BIRTHDAY_GIFT_MIN_HOLD_PCT AND
 * trailing-30-day purchase >= config.BIRTHDAY_GIFT_MIN_30D_PURCHASE). The
 * month filter is what makes this the "gift them now" list, separate from
 * Birthdays · Last 3 Days. Locked, self-excluded, and TAB players are omitted
 * upstream. The gift draft is review-only, gated the same way as Birthdays.
 */
import type { Dict } from "./../types";
import { esc } from "./../format";
import { aidHtml, ltpHtml, holdHtml, purchaseMoneyHtml, ticketHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function sortBirthdayGift(rows: Dict[], mode: string): Dict[] {
  const copy = [...rows];
  if (mode === "ltpHigh")
    return copy.sort((a, b) => (b.lifetimePurchasedNum || 0) - (a.lifetimePurchasedNum || 0));
  if (mode === "holdHigh")
    return copy.sort((a, b) => (b.holdPctNum || 0) - (a.holdPctNum || 0));
  if (mode === "name")
    return copy.sort((a, b) => String(a.lastName || a.name).localeCompare(String(b.lastName || b.name)));
  // Default: highest 30-day purchase first (rows arrive already ordered).
  return copy;
}

export function viewBirthdayGift(): string {
  return tableCard({
    rows: rowsFor("birthdayGift"), stateKey: `bgift_${app.agent}`,
    pagerNote: "Hold >= 50% and 30-day purchase >= $4,000",
    showSearch: true, extraKeys: ["email", "firstName", "lastName"],
    forcePaginate: true, pageSize: 10,
    sortOptions: [
      { value: "p30High", label: "Sort: 30D Purchase ↓" },
      { value: "ltpHigh", label: "Lifetime purchase ↓" },
      { value: "holdHigh", label: "Hold % ↓" },
      { value: "name", label: "Name (A–Z)" },
    ],
    defaultSort: "p30High",
    sortFn: sortBirthdayGift,
    headers: ["AID", "Email", "First Name", "Last Name", "Birthday", "Age",
      "Hold %", "30D Purchase", "LTP", "Ticket"],
    align: ["left", "left", "left", "left", "left", "right", "right", "right", "right", "center"],
    markerCol: 4,
    empty: "No gift-eligible birthdays this month (Hold and 30-day spend thresholds).",
    renderRow: (p) => [aidHtml(p), esc(p.email), esc(p.firstName), esc(p.lastName),
      `<span class="t-success w-semibold">${esc(p.birthday)}</span>`, esc(p.age ?? "—"),
      holdHtml(p.holdPct), purchaseMoneyHtml(p.purchase30d, p.purchase30dNum),
      ltpHtml(p.lifetimePurchase, p.lifetimePurchasedNum), ticketHtml(p)],
  });
}
