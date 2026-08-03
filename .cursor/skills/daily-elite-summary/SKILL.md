---
name: daily-elite-summary
description: Generates the Elite Sun–Thu morning report through the weekday router, including same-weekday comparison and the Top 20 Same Day Comparison. Use when the user asks for an Elite daily summary, morning Elite report, weekend summary, or the 10:00 AM Israel workflow.
---

# Elite Morning Flow (Sun–Thu, 10:00 AM Israel)

**Canonical workflow:** [`daily_summary/DAILY_SUMMARY.md`](../../../daily_summary/DAILY_SUMMARY.md)

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Terminology**, **Elite
managed book**, **Revenue and Purchased players**, **Account status and
decline reasons**.

## Schedule

| Generation day | Action |
|----------------|--------|
| **Sunday 10:00 AM Israel** | `python daily_summary/generate_morning_elite.py` → weekend (prior Thu–Sat) |
| **Mon–Thu 10:00 AM Israel** | Same router → daily (yesterday) |
| **Fri/Sat** | Skip — no scheduled run |
| **On request** | `--force daily\|weekend` or `--date YYYY-MM-DD` |
| **In Cursor** | `@daily-elite-summary` or "run morning elite" |

Register Windows task (once): `powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1`

Router entry point: `daily_summary/generate_morning_elite.py`

## Format baselines (locked)

Diff against these — do not re-negotiate layout in chat.

| Report | Baseline | Reference |
|--------|----------|-----------|
| **Daily** (Mon–Thu) | **2026-07-07** | `daily_summary/daily_summaries/2026-07-07_elite_daily_summary_canvas.html` |
| **Weekend** (Sunday) | **2026-07-12** format lock | `daily_summary/daily_summaries/2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html` |

The HTML files are the durable layout references. Regenerate the corresponding
`.canvas.tsx` when an interactive diff is required.

## Output

- **Markdown (daily):** `daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary.md`
- **Canvas (daily):** `canvases/elite-daily-summary-YYYY-MM-DD.canvas.tsx` (search + agent + reason filters)
- **Canvas (weekend):** `canvases/elite-weekend-summary-YYYY-MM-DD_to_YYYY-MM-DD.canvas.tsx` (3-day bundle, 60 players)
- **Report date:** yesterday by default for daily (`--date YYYY-MM-DD` to pin)
- **Day compare:** report date vs **prior same weekday**

After running, open the dated canvas beside chat.

## Report sections (in order)

1. **{Weekday} vs last {weekday} · Elite & Jackpota** — platform + Elite WoW
2. **Top 20 Same Day Comparison** — LT Purchase, Lifetime Hold, urgency, Reason, Recommendation
3. **Per-player handoffs** — `@wow-drop-reason-analysis` + `wow_drop_player_handoff.py`

For **overall / Jackpota vs Elite** questions: read the dated markdown summary or
run this skill. Definitions: `Elite.MD` **Terminology** (Overall), **Elite
managed book**, and **Revenue and Purchased players** (account-day KPI
aggregation is mandatory).

**Inactive / suspicious players:** If offline, restricted, redeem-stuck,
**same-weekday skip**, or Reason incomplete — check Zendesk **description +
tags** before purchase push (skip may be POA/KYC block). See `Elite.MD`
**Account status and decline reasons**.

**Not in daily summary** (run separately): `python decline_check/generate_decline_protocol.py` for rolling 7d decline cohort.

## Terminology

Apply `.cursor/rules/elite-core.mdc` and `.cursor/rules/bigquery-analytics.mdc`.
Use **Purchased players**, **Revenue**, **Reason**, and **Recommendation**. No
book-level Churn count belongs in the daily summary. For deeper definitions,
consult only the matching `Elite.MD` section from Contents (do not restate the
glossary here).

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.
