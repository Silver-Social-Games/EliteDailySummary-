/** Top 10 Purchasers — yesterday's biggest spenders. */
import { esc } from "./../format";
import { aidHtml } from "./../cells";
import { rowsFor } from "./../selectors";
import { app } from "./../state";
import { tableCard } from "./../table";

function offerCell(p: Record<string, unknown>): string {
  const code = String(p.offerCode || "—");
  const title = String(p.offerTitle || "");
  if (code === "—") return code;
  const qty = Number(p.offerQty || 0);
  const qtyHint = qty > 1 ? `<span class="t-tertiary t-small"> ×${qty}</span>` : "";
  return `<span class="top10-offer" title="${esc(title || code)}">${esc(code)}</span>${qtyHint}`;
}

function priceCell(p: Record<string, unknown>): string {
  const price = esc(p.offerPrice);
  const avg = p.offerPriceVaries ? `<span class="t-warning t-small"> avg</span>` : "";
  return `<span class="top10-money">${price}</span>${avg}`;
}

function frequent30Cell(p: Record<string, unknown>): string {
  const price = String(p.frequentLast30d || "—");
  const orders = Number(p.usualPriceOrders || 0);
  if (price === "—") return price;
  return orders > 1
    ? `<span class="top10-money">${esc(price)}</span> <span class="t-tertiary t-small">×${orders}</span>`
    : `<span class="top10-money">${esc(price)}</span>`;
}

export function viewTop10(): string {
  return tableCard({
    rows: rowsFor("top10"), stateKey: `t10_${app.agent}`,
    extraKeys: ["offerCode", "offerTitle"], cardClass: "top10-card",
    showSearch: false,
    headers: ["#", "AID", "Name", "Purchased $", "Purchases", "Top Offer", "Price",
              "Frequent 30d", "Max Purchase 30D"],
    align: ["center", "left", "left", "right", "right", "left", "right", "right", "right"],
    markerCol: 3,
    tableClass: "top10-grid",
    empty: "No purchasers yesterday.",
    renderRow: (p) => [esc(p.rank), aidHtml(p), `<span class="top10-name">${esc(p.name)}</span>`,
      `<span class="t-success w-semibold top10-money">${esc(p.purchased)}</span>`,
      esc(p.orderCount), offerCell(p), priceCell(p),
      frequent30Cell(p),
      `<span class="top10-money">${esc(p.maxPurchase30d || "—")}</span>`],
  });
}
