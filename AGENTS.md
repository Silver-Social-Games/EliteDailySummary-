# AGENTS.md — Elite Analytics Project

BigQuery Elite (managed VIP) analytics for `silver-social-games-data` (EU).  
**Canonical reference:** [`Elite.MD`](Elite.MD)

---

## What this project is

**New work:** create a **dedicated top-level folder** per initiative (e.g. `vip_event/`, not `decline_check/`). Each folder holds its own generator, `exports/`, and `handoffs/`. Reuse BigQuery helpers from `decline_check/generate_daily_elite_summary.py` via import — do not pile unrelated deliverables into `decline_check/`.

| Area | Path |
|------|------|
| Definitions, SQL, dashboard alignment | `Elite.MD` |
| **VIP Event (Vegas Top 30)** | `vip_event/VIP_EVENT.md` · `vip_event/generate_vegas_top30_elite_brief.py` |
| **60 Days No Purchase Last Push** (quarterly) | `last_push_60d/LAST_PUSH_60D.md` · `last_push_60d/generate_60_days_no_purchase_last_push.py` · `last_push_60d/exports/` |
| **Purchase lookup** | `purchase_lookup/PURCHASE_LOOKUP.md` · `purchase_lookup/generate_purchase_lookup.py` · skill `@purchase-lookup` |
| **Daily summary** | `daily_summary/DAILY_SUMMARY.md` · `daily_summary/generate_morning_elite.py` · `daily_summary/daily_summaries/` |
| Daily flow | `daily_summary/DAILY_SUMMARY.md` · legacy `decline_check/DAILY_FLOW.md` |
| Daily summary generator (legacy) | `decline_check/generate_daily_elite_summary.py` |
| Daily summary canvas | `decline_check/generate_daily_elite_canvas.py` · template in `decline_check/handoffs/` |
| Daily reports (legacy) | `decline_check/daily_summaries/` |
| Enterprise SQL copies | `decline_check/*.sql` |
| Decline playbook | `decline_check/ACTION_PLAYBOOK.md` |
| Daily summary skill | `.cursor/skills/daily-elite-summary/SKILL.md` |
| WoW drop handoff skill | `.cursor/skills/wow-drop-reason-analysis/SKILL.md` |
| WoW drop handoffs | `decline_check/handoffs/` |
| Feedback CRO canvas | `decline_check/FEEDBACK_CRO_CANVAS.md` · `decline_check/generate_elite_feedback_cro_canvas.py` · skill `@elite-feedback-cro` |

**Not included:** workshop e-commerce CSVs, gold-layer transformations, or generic analytics practice folders.

---

## Terminology (mandatory)

Read `Elite.MD` before reporting.

| Term | Rule |
|------|------|
| **Elite** | Managed book — use **Elite**, not "VIP" in reports |
| **AID** | Always show `account_id` as **AID** |
| **Bought** | `purchased > 0` after account-level KPI agg |
| **Purchased players** | Distinct Elite with purchased > 0 that day — not "Buyers" or "Players who purchased" |
| **Overall (platform)** | All players — `GROUP BY account_id, date` on KPIs first; see `Elite.MD` § Overall vs Elite |
| **Revenue (dashboard)** | `dbt_aninditac.elite` + `daily_player_revenue_kpis.purchased` (account-level agg first) |
| **Agent** | `tag_agent_1` from `dbt_utils.elite_account_tags` |
| **Churn** | No purchase in last **7** calendar days |
| **Active decliner** | Bought last 7d but **less** than prior 7d week |
| **Account check** | Always `uam_accounts.locked` + `lock_reason` before drop-reason conclusions |

---

## Stack

| Component | Technology |
|-----------|------------|
| Warehouse | BigQuery `silver-social-games-data` |
| Elite book (revenue) | `dbt_aninditac.elite` |
| Daily KPIs | `jackpota_agg.daily_player_revenue_kpis` |
| Payments reconcile | `transactional_data.payment_payment_orders` |
| Orchestration | Python 3.8+ |

---

## Setup

```bash
cd "c:\Users\Owner\Downloads\Elite"
pip install -r requirements.txt
```

**Credentials:** `GOOGLE_APPLICATION_CREDENTIALS` or default `c:\Users\Owner\Downloads\key.json.json`

---

## Daily workflow

**Schedule:** Sun–Thu at **10:00 AM Israel time** via weekday router:

```bash
python daily_summary/generate_morning_elite.py
```

| Generation day | Report | Script path |
|----------------|--------|-------------|
| **Sunday** | Prior Thu + Fri + Sat | weekend |
| **Mon–Thu** | Yesterday | daily |
| **Fri/Sat** | *(skip)* | — |

Manual override:

```bash
python daily_summary/generate_morning_elite.py --force weekend
python daily_summary/generate_morning_elite.py --force daily --date 2026-07-07
python daily_summary/generate_daily_summary.py --date YYYY-MM-DD
```

### Format baselines (locked)

Diff against these — do not re-negotiate layout in chat.

| Report | Baseline | Reference |
|--------|----------|-----------|
| **Daily** (Mon–Thu) | **2026-07-07** | `canvases/elite-daily-summary-2026-07-07.canvas.tsx` · `daily_summaries/2026-07-07_elite_daily_summary_canvas.html` |
| **Weekend** (Sunday) | **2026-07-12** format lock | `canvases/elite-weekend-summary-2026-07-09_to_2026-07-11.canvas.tsx` · `daily_summaries/2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html` |

Schedule (Windows, once — **10:00 AM Israel time**):

```powershell
powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1
```

In Cursor: `@daily-elite-summary` or "run elite daily summary"

---

## MCP / scan limits

- Use `dbt_aninditac.elite` for revenue (Yesterday Performance dashboard parity).
- **Never** `SUM(purchased)` on raw `daily_player_revenue_kpis` — always `GROUP BY account_id, date` first (`Elite.MD` § KPI grain).
- For **overall + Elite yesterday**, read `daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary.md` or run the daily summary script — do not improvise platform totals.
- `uam_account_category_tags` with JSON filter often exceeds **1 GB** MCP cap — use `dbt_utils.elite_account_tags` or Python + service account for heavy queries.

---

## Do not

- Use workshop CSV data unless the user explicitly asks.
- Conflate Active decliners with Churn or Monday-only skips.
- Use `elite_account_tags`-only book for dashboard revenue without noting ~$1k variance.
- Create extra summary/status markdown files — communicate in chat only.
