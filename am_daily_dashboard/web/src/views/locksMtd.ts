/** Locked tables — shared columns for recent (Last 3 Days) and MTD blocks. */
import { esc } from "../format";
import { aidHtml, unlockHtml } from "../cells";
import { rowsFor } from "../selectors";
import { app } from "../state";
import { tableCard } from "../table";

export const LOCKS_TABLE_HEADERS = [
  "AID", "Name", "Email", "Lock Reason", "Locked Date", "LTP", "Hold %",
  "Days Remaining / Unlock",
];
export const LOCKS_TABLE_ALIGN = [
  "left", "left", "left", "left", "left", "right", "right", "left",
] as const;

export function lockTableRowCells(p: Record<string, unknown>): string[] {
  return [
    aidHtml(p),
    esc(p.name),
    esc(p.email || "—"),
    `<span class="t-${p.tone || "warning"}">${esc(p.lockReason)}</span>`,
    `<span class="t-small">${esc(p.created || p.lockedAt || "—")}</span>`,
    esc(p.lifetimePurchase || "—"),
    esc(p.lifetimeHold || "—"),
    unlockHtml(p.unlockDetail, p.unlockRemainingDays),
  ];
}

export function locksMtdTableCard(): string {
  return tableCard({
    rows: rowsFor("locksMtd"), stateKey: `lkm_${app.agent}`, showSearch: true,
    title: "Locked · MTD · this calendar month",
    headers: [...LOCKS_TABLE_HEADERS],
    align: [...LOCKS_TABLE_ALIGN], markerCol: 3,
    empty: "No accounts locked this month.",
    renderRow: (p) => lockTableRowCells(p),
  });
}
