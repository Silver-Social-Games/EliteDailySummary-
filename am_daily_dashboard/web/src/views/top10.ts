/** Top 10 Purchasers — yesterday's biggest spenders.
 *
 * `packageFit` is the Usual → Ceiling cell, formatted once by
 * build_package_fit in Python for all three implementations. A 7D/30D average
 * was built and rejected: these players buy at 15-25 price points a month, so a
 * mean names no sellable package.
 */
import { esc } from "./../format";
import { aidHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

export function viewTop10(): string {
  return tableCard({
    rows: rowsFor("top10"), stateKey: `t10_${app.agent}`,
    extraKeys: ["offerCode", "offerTitle"], compact: true,
    headers: ["#", "AID", "Name", "Purchased $", "Purchases (#)", "Top Offer", "Price", "Usual → Ceiling (30D)"],
    align: ["center", "left", "left", "right", "right", "left", "right", "left"], markerCol: 3,
    empty: "No purchasers yesterday.",
    renderRow: (p) => [esc(p.rank), aidHtml(p), esc(p.name),
      `<span class="t-success w-semibold">${esc(p.purchased)}</span>`,
      esc(p.orderCount), esc(p.offerCode),
      `<span class="${p.offerPriceVaries ? "t-warning" : ""}">${esc(p.offerPrice)}${p.offerPriceVaries ? " avg" : ""}</span>`,
      esc(p.packageFit)],
  });
}
