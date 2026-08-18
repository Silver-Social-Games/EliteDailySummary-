---
name: elite-feedback-cro
description: Produces an Elite negative-feedback CRO canvas by parsing Excel feedback, tagging themes, and joining BigQuery Purchased and NGR metrics. Use when the user requests an Elite feedback analysis, CRO canvas, complaint-impact report, or feedback export.
---

# Elite Negative Feedback — CRO Canvas

**Canonical workflow:** [`feedback_cro/FEEDBACK_CRO_CANVAS.md`](../../../feedback_cro/FEEDBACK_CRO_CANVAS.md)

## When to use

- New **Elite Feedback.xlsx** from agents / Zendesk
- CRO brief on **negative complaints** with spend impact
- Shareable **HTML** matching the Cursor canvas (pie filter, dark theme, full table)

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python feedback_cro/generate_elite_feedback_cro_canvas.py
```

Custom Excel path:

```bash
python feedback_cro/generate_elite_feedback_cro_canvas.py --xlsx "path/to/Elite Feedback.xlsx"
```

Pin comparison windows for a reproducible rerun:

```bash
python feedback_cro/generate_elite_feedback_cro_canvas.py --before-start 2026-04-22 --before-end 2026-05-18 --after-start 2026-05-19 --after-end 2026-07-18
```

`--after-end` defaults to today. Always pin it for a historical or shared report.

Exports always copy to `VIP\Elite_Cursor\Feedback CRO`. `--copy-desktop` is optional.

**Cursor:** `@elite-feedback-cro` or "run elite feedback CRO canvas" / "export feedback report".

## Default source file

`C:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Elite_Cursor\Feedback CRO\Elite Feedback.xlsx`

(OneDrive lock: script copies to workspace temp before read.)

## Outputs

| Artifact | Path |
|----------|------|
| Live canvas | `~/.cursor/projects/<workspace>/canvases/elite-feedback-cro.canvas.tsx` |
| Canvas backup | `feedback_cro/handoffs/elite-feedback-cro.canvas.tsx` |
| HTML export (canvas-style) | `VIP\Elite_Cursor\Feedback CRO\elite-feedback-cro-export.html` |
| Markdown export | `VIP\Elite_Cursor\Feedback CRO\elite-feedback-cro-export.md` |

Open canvas: `Ctrl + P` → paste live canvas path → **Open Canvas**.

## Report contents

1. **Header** — Before / After windows (equal 27 days split on 19 May)
2. **Stats** — total feedback entries, negative players, cohort purchased & NGR change
3. **Bar chart** — cohort purchased & NGR before vs after
4. **Pie** — tag themes with names + %; click slice/legend/pill to filter table
5. **Player table** — feedback words, lifetime purchased, purchased/NGR before/after/change
6. **Expandable feedback** — full verbatim quotes per player

## Counts (explain when asked)

| Term | Meaning |
|------|---------|
| Total feedback entries | Rows with text in Excel (e.g. 41) |
| Negative players | Unique AIDs with ≥1 negative theme after merge (e.g. 31) |
| Excluded | Empty or purely positive unique players (e.g. 4) |
| Tag mentions | Pie total; one player can have multiple tags |

## Metrics

Definitions: [`Elite.MD`](../../../Elite.MD) **Terminology** (NGR) and
**Revenue and Purchased players**.

- **Purchased / NGR** from `jackpota_agg.daily_player_revenue_kpis` — `GROUP BY account_id, date` first
- **Before:** defaults to 22 Apr – 18 May · **After:** defaults to 19 May – today
- Negative-only: exclude purely positive; mixed feedback keeps full text

Before each run, confirm the intended comparison cutoff and use CLI date options;
do not edit date constants in the generator.

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.

## Generator

`feedback_cro/generate_elite_feedback_cro_canvas.py` — single entry point for canvas + exports.
