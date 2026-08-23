/** Open Tickets — open Zendesk tickets on this AM's book.
 *
 * TIDs always link to Zendesk. TID means Zendesk ticket ID, never a payment or
 * transaction identifier.
 *
 * Default sort: Priority Score (weighted financial signals × topic multiplier).
 * Tier badges: Withdrawal/Security = danger, Account/KYC/Promo = warning,
 * Service Issue = info, General = plain text.
 */
import { esc } from "./../format";
import { aidHtml, holdHtml, ltpHtml, purchaseMoneyHtml, ticketIdsHtml } from "./../cells";
import { sortByNumKey } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function whenLine(label: string, date: string, days: unknown): string {
  const age = typeof days === "number" ? ` · ${days}d` : "";
  return `<div class="ticket-when-line"><span class="ticket-when-label">${esc(label)}</span><span class="ticket-when-date">${esc(date)}${esc(age)}</span></div>`;
}

function ticketWhenCell(p: Record<string, unknown>): string {
  return `<div class="ticket-when">${whenLine("Created", String(p.ticketCreated || "—"), p.ticketAgeDays)}${whenLine("Updated", String(p.ticketUpdated || "—"), p.ticketUpdatedAgeDays)}</div>`;
}

function topicBadge(label: string, mult: number): string {
  if (mult >= 2.0) return `<span class="badge danger">${esc(label)}</span>`;
  if (mult >= 1.5) return `<span class="badge warning">${esc(label)}</span>`;
  if (mult >= 1.2) return `<span class="badge info">${esc(label)}</span>`;
  return `<span class="badge neutral-soft">${esc(label)}</span>`;
}

function topicCell(p: Record<string, unknown>): string {
  const labels: string[] = Array.isArray(p.topicLabels) && p.topicLabels.length
    ? p.topicLabels.map(String)
    : [String(p.topicLabel ?? "General")];
  const mult = Number(p.topicMult ?? 1.0);
  const secondaryMult = Math.max(1.0, mult - 0.3);
  const unique = [...new Set(labels)].slice(0, 2);
  return `<div class="topic-stack">${unique.map((label, i) =>
    topicBadge(label, i === 0 ? mult : secondaryMult)).join("")}</div>`;
}

export function viewTickets(): string {
  return tableCard({
    rows: rowsFor("zendesk"), stateKey: `zd_${app.agent}`, extraKeys: ["ticketIds"],
    sortOptions: [
      { value: "score",     label: "Sort: Priority ↓" },
      { value: "ltp",       label: "Sort: LTP ↓" },
      { value: "tickets",   label: "Sort: Open Tickets ↓" },
      { value: "purchase7d", label: "Sort: 7D Purchase ↓" },
      { value: "created", label: "Sort: Oldest created" },
      { value: "updated", label: "Sort: Stale updated" },
    ],
    defaultSort: "score",
    sortFn: (rows, s) =>
      s === "tickets"    ? sortByNumKey(rows, "openTickets", true)
      : s === "ltp"      ? sortByNumKey(rows, "lifetimePurchasedNum", true)
      : s === "purchase7d" ? sortByNumKey(rows, "purchase7dNum", true)
      : s === "created"  ? sortByNumKey(rows, "ticketAgeDays", true)
      : s === "updated"  ? sortByNumKey(rows, "ticketUpdatedAgeDays", true)
      : sortByNumKey(rows, "priorityScore", true),
    headers: ["AID", "Name", "Topic", "Created / Updated", "LTP", "Hold", "7D", "Open", "Ticket"],
    align: ["left", "left", "left", "left", "right", "right", "right", "center", "center"],
    markerCol: 3,
    empty: "No open tickets.",
    renderRow: (p) => [
      aidHtml(p),
      esc(p.name),
      topicCell(p),
      ticketWhenCell(p),
      ltpHtml(p.lifetimePurchase || "$0", p.lifetimePurchasedNum),
      holdHtml(p.lifetimeHold || "n/a"),
      purchaseMoneyHtml(p.purchase7d || "$0", p.purchase7dNum),
      esc(p.openTickets),
      ticketIdsHtml(p),
    ],
  });
}
