/** Top 20 · WoW Purchase Gaps — same-weekday drops, up to 20 per AM.
 *
 * Selection and classification are shared with Elite Daily Decline
 * (wow_drop_analysis.fetch_top_same_day_by_agent); soften_decline_rows only
 * adjusts tone. Canvas counterpart: canvas_parts/tables.py Top20DeclineTable.
 *
 * This is the one section that does not use tableCard: it has a reason-chip
 * filter row and a totals row, neither of which the generic card offers.
 */
import { TITLES } from "./../payload";
import { esc, icon, money } from "./../format";
import { aidHtml, holdHtml, ltpHtml, moneyHtml, p7dHtml, ticketHtml, urgencyHtml } from "./../cells";
import { renderAction, renderReason } from "./../reason";
import { matchesDecline, sortPlayers } from "./../filters";
import { rowsFor } from "./../selectors";
import { app, getState } from "./../state";
import { paginate, tableHtml } from "./../table";

export function viewTop20(): string {
  const players = rowsFor("decline");
  const stateKey = `dec_${app.agent}`;
  const search: string = getState(stateKey + "_search", "");
  const reason: string = getState(stateKey + "_reason", "all");
  const sortBy: string = getState(stateKey + "_sortBy", "urgency");
  const reasons = [...new Set(players.map((p) => p.reason).filter(Boolean))].sort();
  const ordered = sortPlayers(players.filter((row) =>
    (reason === "all" || row.reason === reason) && matchesDecline(row, search)), sortBy);
  const { slice, pager, total } = paginate(ordered, stateKey, { forceOn: true, defaultSize: 10 });
  const priorTotal = ordered.reduce((sum, p) => sum + (p.priorPriorNum || 0), 0);
  const active = search.trim() !== "" || reason !== "all";

  const headers = ["#", "AID", "Name", TITLES.lifetimePurchase, TITLES.lifetimeHold,
    TITLES.thisPurchase, TITLES.priorPurchase, TITLES.purchase7d,
    "Urgency", "Reason", "Recommendation", "Ticket"];
  const rows = slice.map((p) => [
    String(ordered.indexOf(p) + 1),
    aidHtml(p), esc(p.name),
    ltpHtml(p.lifetimePurchase, p.lifetimePurchasedNum),
    holdHtml(p.lifetimeHold),
    moneyHtml(p.thisDay, p.zeroDay ? "low" : "neutral"),
    moneyHtml(p.priorDay, (p.sortGap || 0) >= 2000 ? "high" : "neutral"),
    p7dHtml(p.purchase7d, p.purchase7dNum), urgencyHtml(p.urgency),
    `<div class="reason-cell">${renderReason(p.reasonParts, p.reasonTable || p.reason)}</div>`,
    `<div class="action-cell">${renderAction(p.recommendation)}</div>`,
    ticketHtml(p),
  ]);
  const tones = slice.map((p) => p.tone || "neutral");
  if (rows.length) {
    rows.push(["", "", "Total (all filtered)", "", "", "", money(priorTotal), "", "", "", "", ""]);
    tones.push("neutral");
  }
  return `<div class="card">
        <div class="toolbar">
          <label class="search">${icon("search", "ic-sm")}
            <input type="search" placeholder="Search name, AID, reason…" value="${esc(search)}" data-state="${esc(stateKey + "_search")}">
          </label>
          <span class="select-wrap"><select data-state="${esc(stateKey + "_sortBy")}">
            <option value="urgency" ${sortBy === "urgency" ? "selected" : ""}>Sort: Urgency + gap</option>
            <option value="priorHigh" ${sortBy === "priorHigh" ? "selected" : ""}>Prior purchase ↓</option>
            <option value="lifetimeHigh" ${sortBy === "lifetimeHigh" ? "selected" : ""}>Lifetime purchase ↓</option>
            <option value="gapHigh" ${sortBy === "gapHigh" ? "selected" : ""}>WoW gap ↓</option>
          </select>${icon("chev-down", "ic-xs")}</span>
          <div class="spacer"></div>
          <span class="badge ${active ? "brand" : ""}">${active ? `${ordered.length} of ${players.length}` : `${players.length} players`}</span>
        </div>
        ${reasons.length ? `<div class="chip-row">
          <button type="button" class="chip ${reason === "all" ? "active" : ""}" data-reason-state="${esc(stateKey + "_reason")}" data-reason="all">All reasons</button>
          ${reasons.map((r) => `<button type="button" class="chip ${reason === r ? "active" : ""}" data-reason-state="${esc(stateKey + "_reason")}" data-reason="${esc(r)}">${esc(r)}</button>`).join("")}
        </div>` : ""}
        ${tableHtml(headers, rows,
          ["center", "left", "left", "right", "right", "right", "right", "left", "center", "left", "left", "center"],
          tones,
          { tableClass: "players-table", totalRowIndex: rows.length - 1,
            empty: "No players match the current filters." })}
        ${total ? pager : ""}
      </div>`;
}
