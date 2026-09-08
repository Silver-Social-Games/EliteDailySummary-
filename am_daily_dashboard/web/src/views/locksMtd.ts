/** Locked · MTD — accounts locked this calendar month (all reasons).
 * Rendered inside the Lock & TAB view, not a separate sidebar tab. */
import { esc } from "../format";
import { aidHtml } from "../cells";
import { rowsFor } from "../selectors";
import { app } from "../state";
import { tableCard } from "../table";

export function locksMtdTableCard(): string {
  return tableCard({
    rows: rowsFor("locksMtd"), stateKey: `lkm_${app.agent}`, showSearch: true,
    title: "Locked · MTD · this calendar month",
    headers: ["AID", "Name", "Email", "Lock Reason", "Locked Date", "LTP", "Hold %"],
    align: ["left", "left", "left", "left", "left", "right", "right"], markerCol: 3,
    empty: "No accounts locked this month.",
    renderRow: (p) => [aidHtml(p), esc(p.name), esc(p.email || "—"),
      `<span class="t-${p.tone || "warning"}">${esc(p.lockReason)}</span>`,
      `<span class="t-small">${esc(p.created || p.lockedAt || "—")}</span>`,
      esc(p.lifetimePurchase || "—"), esc(p.lifetimeHold || "—")],
  });
}
