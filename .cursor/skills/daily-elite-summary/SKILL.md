---
name: daily-elite-summary
description: Elite Sun–Thu morning flow — weekday router (Sun=weekend Thu–Sat, Mon–Thu=daily). Same weekday compare, Top 20 Same Day Comparison from BigQuery. Use at 10:00 AM Israel time, for "elite daily summary", "morning elite report", or @daily-elite-summary.
---

# Elite Morning Flow (Sun–Thu, 10:00 AM Israel)

**Canonical workflow:** [`daily_summary/DAILY_SUMMARY.md`](../../../daily_summary/DAILY_SUMMARY.md)

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
| **Daily** (Mon–Thu) | **2026-07-07** | `canvases/elite-daily-summary-2026-07-07.canvas.tsx` |
| **Weekend** (Sunday) | **2026-07-12** format lock | `canvases/elite-weekend-summary-2026-07-09_to_2026-07-11.canvas.tsx` |

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

For **overall yesterday + Elite** questions: read the dated markdown summary or run this skill — use `Elite.MD` § Overall vs Elite (account-level KPI agg mandatory).

**Inactive / suspicious players:** If offline, restricted, redeem-stuck, **same-weekday skip**, or Reason incomplete — check Zendesk **description + tags** before purchase push (skip may be POA/KYC block). See `Elite.MD` § Inactive / suspicious — Zendesk drill-down.

**Not in daily summary** (run separately): `python decline_check/generate_decline_protocol.py` for rolling 7d decline cohort.

## Terminology

Read `Elite.MD`. Use **Purchased players**, **Revenue**, **Reason**, **Recommendation**. No book-level churn count in the daily summary.

## Credentials

`GOOGLE_APPLICATION_CREDENTIALS` or `c:\Users\Owner\Downloads\key.json.json`
