/** Export the current view's visible table to CSV — plain text, no HTML. */
import { REPORT, TITLES } from "./payload";
import { app, getState } from "./state";
import { VIEWS } from "./registry";
import { rowsFor } from "./selectors";
import { matchesDecline, sortPlayers } from "./filters";
import { toast } from "./toast";

function csvEscape(v: unknown): string {
  const s = String(v ?? "").replace(/"/g, '""');
  return /[",\n\r]/.test(s) ? `"${s}"` : s;
}

function downloadCsv(filename: string, headers: string[], rows: string[][]): void {
  const lines = [headers.map(csvEscape).join(",")];
  for (const row of rows) lines.push(row.map(csvEscape).join(","));
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function top20Rows(): { headers: string[]; rows: string[][] } {
  const stateKey = `dec_${app.agent}`;
  const search: string = getState(stateKey + "_search", "");
  const reason: string = getState(stateKey + "_reason", "all");
  const sortBy: string = getState(stateKey + "_sortBy", "urgency");
  const players = rowsFor("decline");
  const ordered = sortPlayers(
    players.filter((row) => (reason === "all" || row.reason === reason) && matchesDecline(row, search)),
    sortBy
  );
  const headers = [
    "#", "AID", "Name", "LT Purchase", "Lifetime Hold", TITLES.thisPurchase, TITLES.priorPurchase,
    "7D PURCHASE", "Urgency", "Reason", "Recommendation", "Ticket",
  ];
  const rows = ordered.map((p, i) => [
    String(i + 1),
    String(p.aid ?? ""),
    String(p.name ?? ""),
    String(p.lifetimePurchase ?? ""),
    String(p.lifetimeHold ?? ""),
    String(p.thisDay ?? ""),
    String(p.priorDay ?? ""),
    String(p.purchase7d ?? ""),
    String(p.urgency ?? ""),
    String(p.reasonTable || p.reason || ""),
    String(p.recommendation ?? ""),
    p.ticketEnabled ? "Draft" : String(p.ticketDisabledReason || ""),
  ]);
  return { headers, rows };
}

function genericRows(key: string, headers: string[], fields: string[]): { headers: string[]; rows: string[][] } {
  const rows = rowsFor(key).map((p) => fields.map((f) => String(p[f] ?? "")));
  return { headers, rows };
}

export function exportCurrentViewCsv(): void {
  const v = VIEWS[app.view];
  if (!v || v.comingSoon) return;
  const date = REPORT.date || "export";
  const slug = (v.short || v.label).replace(/[^\w]+/g, "_").slice(0, 40);
  let pack: { headers: string[]; rows: string[][] } | null = null;

  if (app.view === "top20") pack = top20Rows();
  else if (app.view === "top10") {
    pack = genericRows("top10",
      ["#", "AID", "Name", "Purchased", "Top Offer", "Price", "Frequent 30d", "Max Purchase 30D", "LTP", "Hold"],
      ["rank", "aid", "name", "purchased", "offerCode", "offerPrice", "frequentLast30d", "maxPurchase30d", "lifetimePurchase", "lifetimeHold"]);
  } else if (app.view === "tickets") {
    pack = genericRows("zendesk",
      ["AID", "Name", "Topic", "Priority", "Open tickets", "LTP", "7D Purchase"],
      ["aid", "name", "topicLabel", "priorityScore", "openTickets", "lifetimePurchase", "purchase7d"]);
  } else if (app.view === "rd") {
    pack = genericRows("rdOver5k",
      ["AID", "Name", "Amount", "Created", "Won Yesterday", "Docs"],
      ["aid", "name", "amount", "created", "wonYesterday", "docsStatus"]);
  } else if (app.view === "birthdays") {
    pack = genericRows("birthdays", ["AID", "Name", "Birthday", "Age"],
      ["aid", "name", "birthday", "age"]);
  } else if (app.view === "anniversary") {
    pack = genericRows("anniversary",
      ["AID", "Email", "First Name", "Last Name", "Managed Since", "Anniversary", "LTP", "Hold %", "7D Purchase"],
      ["aid", "email", "firstName", "lastName", "managedDate", "anniversaryDate", "lifetimePurchase", "lifetimeHold", "purchase7d"]);
  } else if (app.view === "birthdayGift") {
    pack = genericRows("birthdayGift",
      ["AID", "Email", "First Name", "Last Name", "Birthday", "Age", "Hold %", "30D Purchase", "LTP"],
      ["aid", "email", "firstName", "lastName", "birthday", "age", "holdPct", "purchase30d", "lifetimePurchase"]);
  } else if (app.view === "responsiveness") {
    pack = genericRows("responsiveness",
      ["AID", "Email", "First Name", "Last Name", "Last Contact", "Days Silent", "Hold %", "30D Purchase", "LTP"],
      ["aid", "email", "firstName", "lastName", "lastContact", "daysSinceTicket", "holdPct", "purchase30d", "lifetimePurchase"]);
  }

  if (!pack || !pack.rows.length) {
    toast("Nothing to export on this view");
    return;
  }
  downloadCsv(`${date}_${slug}_${app.agent}.csv`, pack.headers, pack.rows);
  toast("CSV downloaded");
}

export function viewSupportsCsvExport(viewId: string): boolean {
  return ["top20", "top10", "tickets", "rd", "birthdays", "anniversary", "birthdayGift", "responsiveness"].includes(viewId);
}
