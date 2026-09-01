/** Morning Brief — AM intro, segment hero, focus band, Goals. */
import { amIntro, dailyTriggerMetrics, metricBand, personalSnapshotCards, segmentHero } from "./../components";
import { agentBlock } from "./../selectors";
import { goalsSummaryCard } from "./goals";

export function viewHome(): string {
  const b = agentBlock();
  const f = b.focus || {};
  return `<div class="stack">
        ${amIntro(b.greetingLines || [])}
        ${segmentHero()}
        ${metricBand("Today's focus", dailyTriggerMetrics(f), { subtitle: "Click a metric to open the section", cols: 7 })}
        ${metricBand("Personal Snapshot", personalSnapshotCards(b), { cols: 4 })}
        ${goalsSummaryCard(b.goals)}
      </div>`;
}
