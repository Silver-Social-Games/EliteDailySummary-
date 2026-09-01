/** Locked & Take A Break — new locks, plus breaks due to end.
 *
 * Rows sort by soonest unlock automatically, with no visible control: the
 * ordering is the point of the section, so it is deliberately not something an
 * AM can turn off. Windows live in config.py.
 */
import { esc } from "./../format";
import { aidHtml, unlockHtml } from "./../cells";
import { sortBySoonestUnlock } from "./../filters";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewLocks(): string {
  return tableCard({
    rows: rowsFor("locks"), stateKey: `lk_${app.agent}`, showSearch: false,
    sortFn: (rows) => sortBySoonestUnlock(rows),
    headers: ["AID", "Name", "Lock Reason", "Created", "Days Remaining / Unlock"],
    align: ["left", "left", "left", "left", "left"], markerCol: 2,
    empty: "No new locks or breaks due in the Last 3 Days.",
    renderRow: (p) => [aidHtml(p), esc(p.name),
      `<span class="t-${p.tone || "warning"}">${esc(p.lockReason)}</span>`,
      `<span class="t-small">${esc(p.created || p.lockedAt || "—")}</span>`,
      unlockHtml(p.unlockDetail, p.unlockRemainingDays)],
  });
}
