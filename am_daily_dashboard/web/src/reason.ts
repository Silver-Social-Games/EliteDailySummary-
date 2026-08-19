/** Reason and Recommendation formatting for the Top 20 WoW Gaps table.
 *
 * Icons are inline SVG, never emoji. The reason text itself is produced by
 * wow_drop_analysis/wow_drop_reason.py and softened by soften_decline_rows —
 * nothing here invents or reclassifies a reason, it only decides emphasis.
 */
import { esc, icon } from "./format";

const REASON_EMPHASIS = [
  "Redemption Blocked", "Redemption in progress", "Needs ", "Same weekday skip",
  "Spend Softening", "Offline Since", "Pending RD", "RD $", "Redeem Status ",
  "Take a break", "No Purchases", "Played Today", "Account locked", "Red flag",
];

export function reasonPartIcon(part: string): string {
  const pl = part.toLowerCase();
  if (part.startsWith("Red flag")) return "flag";
  if (part.startsWith("Redemption Blocked")) return "ban";
  if (part.startsWith("Redemption in progress")) return "hourglass";
  if (part.startsWith("Account locked") || part.includes("Suspended")) return "lock";
  if (part.startsWith("Needs Recent Acceptable POA") || pl.includes("poa")) return "file";
  if (part.startsWith("Needs KYC") || pl.includes("verification document")) return "clipboard";
  if (part.startsWith("RD $") || part.startsWith("Pending RD")) return "banknote";
  if (part.startsWith("Same weekday skip")) return "calendar";
  if (part.startsWith("Payment failed")) return "x-circle";
  if (part.startsWith("No Purchases")) return "alert";
  if (part.startsWith("Played Today")) return "slots";
  if (part.startsWith("Redeem Status")) return "clipboard";
  if (part.startsWith("Take a break")) return "clock";
  if (part.startsWith("Spend Softening")) return "trend-down";
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
  if (part.startsWith("Same weekday skip") || part.startsWith("Played Today")) return "t-info";
  return "";
}

export function renderReason(parts: string[] | undefined, text: unknown): string {
  const segments =
    parts && parts.length
      ? parts
      : String(text || "")
          .split("●")
          .map((p) => p.trim())
          .filter(Boolean);
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
  const chunks = String(text || "")
    .split(" · ")
    .filter(Boolean);
  const head = chunks[0] || text || "";
  const tail = chunks.slice(1).join(" · ");
  const name = actionHeadIcon(String(head));
  return (
    `<span class="w-semibold">${name ? icon(name, "ic-xs") + " " : ""}${esc(head)}</span>` +
    (tail ? `<span class="t-tertiary"> · ${esc(tail)}</span>` : "")
  );
}
