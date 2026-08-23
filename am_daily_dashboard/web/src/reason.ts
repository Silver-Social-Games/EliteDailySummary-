/** Reason and Recommendation formatting for the Top 20 WoW Gaps table.
 *
 * Icons are inline SVG, never emoji. The reason text itself is produced by
 * wow_drop_analysis/wow_drop_reason.py and softened by soften_decline_rows —
 * nothing here invents or reclassifies a reason, it only decides emphasis.
 */
import { compactMoney, esc, icon, toNum } from "./format";

/** Drop redundant or noisy reason fragments before render. */
function shouldDropPart(part: string, parts: string[]): boolean {
  const head = parts[0] || "";
  if (/^\$0 vs Prior \$/.test(part) && head.startsWith("Same weekday")) return true;
  if (part.startsWith("Redeem Status") && parts.some((p) => p.startsWith("Redemption in progress"))) {
    return true;
  }
  if (
    part.startsWith("Last Purchase") &&
    head.startsWith("Same weekday") &&
    parts.some((p) => p.includes("Played Today"))
  ) {
    return true;
  }
  if (/\d{1,2} Aug .*(Conversation|Welcome!|Re: \[)/.test(part)) return true;
  if (part === "3 Failed Post-Purchase" && parts.some((p) => p.includes("Failed Checkout"))) return true;
  return false;
}

function compactRdPart(part: string): string | null {
  const total = part.match(/^RD \$(\d[\d,]*) total \((\d+) open\) · latest ID (\d+)$/);
  if (total) {
    return `RD ${compactMoney(toNum(total[1]))} · ${total[2]} open · #${total[3]}`;
  }
  const single = part.match(/^RD \$(\d[\d,]*) \(ID (\d+)\)$/);
  if (single) return `RD $${single[1]} · #${single[2]}`;
  return null;
}

function compactLastPurchase(part: string): string | null {
  const m = part.match(/^Last Purchase (\w+ \d+)(?: \w+)? \$([\d,]+)$/);
  if (m) return `Last ${m[1]} · $${m[2]}`;
  return null;
}

function shortenPart(part: string): string {
  const rd = compactRdPart(part);
  if (rd) return rd;
  const lp = compactLastPurchase(part);
  if (lp) return lp;

  const exact: Record<string, string> = {
    "Same weekday skip": "Weekday skip",
    "Played Today - No Purchase": "Played, no purchase",
    "No Purchases In 7D": "No purchase 7D",
    "No Play In 7D": "No play 7D",
    "Churn - needs reactivation": "Churn",
    "Redemption in progress": "RD in progress",
    "Needs Recent Acceptable POA": "Needs POA",
    self_excluded_account: "Self-excluded",
    "3 Failed Checkout": "3 failed checkout",
    "Restriction Lift Requested": "Lift restriction",
    "Needs Document · Take restrictions off": "Needs doc · lift restriction",
  };
  return exact[part] ?? part;
}

function compactReasonParts(parts: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of parts) {
    if (shouldDropPart(raw, parts)) continue;
    const short = shortenPart(raw);
    if (!short) continue;
    const key = short.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(short);
  }
  return out;
}

function compactActionText(text: string): string {
  let s = text.trim();
  if (!s) return s;
  s = s.replace(/ · Ops Approval To Release$/i, "").replace(/ · Ops Approval$/i, "");
  s = s.replace(
    /clear RD \$(\d[\d,]*) total \((\d+) open · latest ID (\d+)\)/i,
    (_, amt, open, id) => `RD ${compactMoney(toNum(amt))} · ${open} open · #${id}`
  );
  s = s.replace(/clear RD \$(\d[\d,]*) \(ID (\d+)\)/i, (_, amt, id) => `RD $${amt} · #${id}`);

  const chunks = s.split(" · ").filter(Boolean);
  if (chunks.length <= 1) return s;
  const head = chunks[0];
  if (head === "No action" || head === "Push purchase" || head === "Soft check-in only") return head;
  if (head.startsWith("Escalate Ops") || head.startsWith("Escalate Compliance")) {
    const tail = head.startsWith("Escalate Compliance") && /poa/i.test(chunks[1] || "")
      ? "POA"
      : chunks[1];
    return tail ? `${head} · ${tail}` : head;
  }
  if (head.startsWith("Fix payment method")) {
    return [head, chunks[1].toLowerCase()].join(" · ");
  }
  return s;
}

const REASON_EMPHASIS = [
  "Redemption Blocked", "Redemption in progress", "RD in progress", "Needs ", "Same weekday skip",
  "Weekday skip", "Spend Softening", "Offline Since", "Pending RD", "RD $", "Redeem Status ",
  "Take a break", "No Purchases", "No purchase 7D", "No play 7D", "Played Today", "Played, no purchase",
  "Account locked", "Red flag", "Churn",
];

export function reasonPartIcon(part: string): string {
  const pl = part.toLowerCase();
  if (part.startsWith("Red flag")) return "flag";
  if (part.startsWith("Redemption Blocked")) return "ban";
  if (part.startsWith("Redemption in progress") || part.startsWith("RD in progress")) return "hourglass";
  if (part.startsWith("Account locked") || part.includes("Suspended")) return "lock";
  if (part.startsWith("Needs Recent Acceptable POA") || part.startsWith("Needs POA") || pl.includes("poa")) {
    return "file";
  }
  if (part.startsWith("Needs KYC") || pl.includes("verification document")) return "clipboard";
  if (part.startsWith("RD $") || part.startsWith("Pending RD")) return "banknote";
  if (part.startsWith("Same weekday skip") || part.startsWith("Weekday skip")) return "calendar";
  if (part.startsWith("Payment failed")) return "x-circle";
  if (part.startsWith("No Purchases") || part.startsWith("No purchase 7D") || part.startsWith("No play 7D")) {
    return "alert";
  }
  if (part.startsWith("Played Today") || part.startsWith("Played, no purchase")) return "slots";
  if (part.startsWith("Redeem Status")) return "clipboard";
  if (part.startsWith("Take a break")) return "clock";
  if (part.startsWith("Spend Softening")) return "trend-down";
  if (part.startsWith("Churn")) return "alert";
  return "";
}

export function actionHeadIcon(head: string): string {
  const hl = head.toLowerCase();
  if (head.startsWith("Escalate Ops")) return "arrow-right";
  if (head.startsWith("Escalate Compliance")) return "scale";
  if (head.startsWith("Push purchase")) return "dollar";
  if (head.startsWith("Fix payment method")) return "card";
  if (head.startsWith("Remove restriction")) return "unlock";
  if (head.startsWith("Send to Ops")) return "wrench";
  if (head.startsWith("Soft check-in")) return "message";
  if (head.startsWith("Agent call") || head.startsWith("Reactivation")) return "phone";
  if (head.startsWith("No action")) return "check-circle";
  if (hl.includes("no outreach") || hl.includes("no purchase push")) return "hand";
  return "";
}

export function reasonPartClass(part: string): string {
  if (part.startsWith("Red flag")) return "t-danger w-semibold";
  if (part.startsWith("Needs ") || part.includes("Blocked")) return "t-warning w-semibold";
  if (part.startsWith("Escalate") || part.includes("Suspended")) return "t-danger w-semibold";
  if (part.startsWith("Same weekday skip") || part.startsWith("Weekday skip") ||
      part.startsWith("Played Today") || part.startsWith("Played, no purchase")) {
    return "t-info";
  }
  return "";
}

export function renderReason(parts: string[] | undefined, text: unknown): string {
  const raw =
    parts && parts.length
      ? parts
      : String(text || "")
          .split("●")
          .map((p) => p.trim())
          .filter(Boolean);
  const segments = compactReasonParts(raw);
  return segments
    .map((part, i) => {
      const emphasize = i === 0 || REASON_EMPHASIS.some((pfx) => part.startsWith(pfx));
      const name = reasonPartIcon(part);
      const cls = emphasize ? reasonPartClass(part) || "w-semibold" : "";
      const sep = i > 0 ? '<span class="sep">·</span>' : "";
      return sep + `<span class="${cls}">${name ? icon(name, "ic-xs") + " " : ""}${esc(part)}</span>`;
    })
    .join("");
}

export function renderAction(text: unknown): string {
  const compact = compactActionText(String(text || ""));
  const chunks = compact
    .split(" · ")
    .filter(Boolean);
  const head = chunks[0] || compact || "";
  const tail = chunks.slice(1).join(" · ");
  const name = actionHeadIcon(String(head));
  return (
    `<span class="w-semibold">${name ? icon(name, "ic-xs") + " " : ""}${esc(head)}</span>` +
    (tail ? `<span class="t-tertiary"> · ${esc(tail)}</span>` : "")
  );
}
