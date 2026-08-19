/** Morning Brief — the greeting, the focus tiles, Goals and the segment strip. */
import type { Dict } from "./../types";
import { richText } from "./../format";
import { segmentCard, statCard } from "./../components";
import { agentBlock } from "./../selectors";
import { goalsSummaryCard } from "./goals";

export function viewHome(): string {
  const b = agentBlock();
  const f: Dict = b.focus || {};
  const greet = (b.greetingLines || []).map((line: string, i: number) => richText(line, i === 0)).join("");
  const cards = [
    { label: "Open Tickets", value: f.openZd ?? 0, icon: "ticket", view: "tickets",
      tone: f.openZd ? "info" : "success" },
    { label: "Top 20 Decline", value: f.declineCount ?? 0, icon: "trend-down", view: "top20",
      tone: f.declineCount ? "warning" : "success" },
    { label: "Pending RD", value: f.rdOver5k ?? 0, icon: "banknote", view: "rd",
      tone: f.rdOver5k ? "warning" : "success" },
    { label: "Take A Break", value: f.takeABreak ?? 0, icon: "clock", view: "locks",
      tone: f.takeABreak ? "warning" : "success" },
    { label: "Other Locked", value: f.otherLocked ?? 0, icon: "lock", view: "locks",
      tone: f.otherLocked ? "warning" : "success" },
    { label: "Self-Exclusion", value: f.selfExclusion ?? 0, icon: "shield", view: "locks",
      tone: "neutral" },
    { label: "Birthdays (3d)", value: f.birthdays ?? 0, icon: "gift", view: "birthdays",
      tone: f.birthdays ? "brand" : "neutral" },
  ];
  return `<div class="stack">
        ${greet ? `<div class="hero"><div class="stack-6">${greet}</div></div>` : ""}
        <div class="stats">${cards.map(statCard).join("")}</div>
        ${goalsSummaryCard(b.goals)}
        ${segmentCard()}
      </div>`;
}
