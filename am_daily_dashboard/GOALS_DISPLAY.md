# Goals headline display (locked 2026-08-25)

**Status:** Active. Do not change without explicit user approval.

This file is the canonical spec for how goal **headline scores** render in the AM
Brief HTML board. Implementation lives in `web/src/cells.ts` (`goalsScoreDisplay`).

## Rule

Show **percentage only**. Formula:

```
display % = (KPI points earned ÷ 80) × 100
```

One decimal when needed (e.g. `97.5%`, `95.3%`). No trailing `.0`.

## Examples

| Who | KPI points (internal) | Headline display |
|-----|----------------------|------------------|
| Coral | 78 / 80 | **97.5%** |
| Team | 76.2 / 80 | **95.3%** |
| Gabriel | 71.9 / 80 | **89.9%** |
| Perfect KPI block | 80 / 80 | **100%** |

## Where this applies

| Surface | View / file |
|---------|-------------|
| Personal AM goals | Performance → Elite Goals; Morning Brief goals card |
| Team Goals | Manager → Team Goals; Manager Dashboard team card |
| Goals Leaderboard | Manager Dashboard leaderboard Score column |

All three call `goalsScoreDisplay()` in `cells.ts`. Change one function, not three
places.

## Do not show

- Raw point text in the headline (`78 / 80`, `76.2 / 80`)
- `/100` suffix (manager appreciation is a separate track, not in the headline)
- Points-as-percent-of-100 without dividing by 80 (e.g. `78%` for 78 KPI points)

## What stays unchanged

- KPI table columns (Goal, Actual, Pace, Gap, Status) — unchanged
- Score meter bar width — still `(points / 80) × 100` for fill width
- Manager appreciation violet track — separate; not part of the headline %
- Leaderboard **ranking** — still `totalPctOfMax` (mixed 80 vs 100 denominators);
  only the **displayed Score column** uses the rule above

## After any edit to this rule

1. Update `web/src/cells.ts` (`goalsScoreDisplay`, `scoreLegendHtml` if needed)
2. Rebuild: `node am_daily_dashboard/web/build.mjs`
3. Refresh HTML: `python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --html-only`
4. Update this file and `@elite-am-brief` SKILL if wording changed

## References

- [`AM_DAILY_DASHBOARD.md`](AM_DAILY_DASHBOARD.md) — Elite Goals methodology
- [`.cursor/skills/elite-am-brief/SKILL.md`](../.cursor/skills/elite-am-brief/SKILL.md) — run workflow
