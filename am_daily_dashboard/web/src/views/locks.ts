/** Locked & Take A Break — recent locks + Locked MTD (same columns on both). */
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";
import { sortBySoonestUnlock } from "./../filters";
import {
  LOCKS_TABLE_ALIGN,
  LOCKS_TABLE_HEADERS,
  lockTableRowCells,
  locksMtdTableCard,
} from "./locksMtd";

function locksRecentTableCard(): string {
  return tableCard({
    rows: rowsFor("locks"), stateKey: `lk_${app.agent}`, showSearch: true,
    sortFn: (rows) => sortBySoonestUnlock(rows),
    title: "Locked & Take A Break · Last 3 Days",
    headers: [...LOCKS_TABLE_HEADERS],
    align: [...LOCKS_TABLE_ALIGN], markerCol: 3,
    empty: "No new locks or breaks due in the Last 3 Days.",
    renderRow: (p) => lockTableRowCells(p),
  });
}

export function viewLocks(): string {
  return `<div class="stack">
        ${locksRecentTableCard()}
        ${locksMtdTableCard()}
      </div>`;
}
