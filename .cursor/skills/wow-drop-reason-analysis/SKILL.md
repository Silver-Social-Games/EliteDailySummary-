---
name: wow-drop-reason-analysis
description: >-
  Analyzes Elite same-weekday WoW purchase drops, ranks the top 10 AIDs by Delta,
  investigates account, redemption, and purchase-failure reasons, and produces
  an agent handoff canvas. Use when the user asks why an Elite player skipped,
  requests a weekday drop analysis, or needs a drop-reason handoff.
---

# WoW Drop Reason Analysis

Apply `.cursor/rules/elite-core.mdc` and `.cursor/rules/bigquery-analytics.mdc`.

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Elite managed book**,
**Revenue and Purchased players**, **Account status and decline reasons**,
**Terminology** (Same-weekday skip / Churn / Active decliner). Consult those
sections only when deeper definitions are needed.

Elite book: `dbt_aninditac.elite`. Revenue: account-day `purchased` from
`daily_player_revenue_kpis`.

## Compare window

| Term | Rule |
|------|------|
| **Report date** | This weekday (default: yesterday) |
| **Prior weekday** | Report date minus 7 days (Monday vs Monday, Tuesday vs Tuesday) |
| **Delta** | Prior weekday purchased minus this weekday purchased |
| **Same-weekday skip** | Bought prior same weekday, $0 on report weekday — not churn if purchased rest of week |

## Terminology (handoff)

| Term | Rule |
|------|------|
| **Purchased** | KPI `purchased` (say **Purchased**, not Bought, in handoffs) |
| **Orders** | = Purchases (`payment_payment_orders`, succeeded) |
| **Hold %** | (Net Purchase / Purchases) × 100 — show **% only** next to Bonuses % |
| **Bonuses** | Lifetime `sc_reward_amount + sc_envelopes_amount`; % of lifetime Purchased |
| **Pending redeem** | `payment_withdraw_money_requests` where `status = 'pre_authorized'` — show **amount + redeem ID only** (no workflow status codes in handoff) |
| **Total Redeemed** | Confirmed redeems only; date = last confirmed redeem |
| **Numbers** | Use digits (4 not four). Minus on negatives: `-$3,484` |
| **Dates** | Weekday + date: `Monday, 8 Jun 2026` |

## Workflow

### 0. Account status (mandatory — run before any conclusion)

**Always check `uam_accounts` first.** `status = default` does not mean active.

```sql
SELECT locked, locked_at, lock_reason, lock_reason_comment, status AS redeem_workflow_status
FROM `transactional_data.uam_accounts` WHERE id = @aid
```

| Result | Primary reason | Action |
|--------|----------------|--------|
| `locked = TRUE`, `lock_reason = Exclusion` | **Self-exclusion** | Ops / Compliance — **no retention outreach** |
| `locked = TRUE`, other reason | **Account locked** | Ops — not agent purchase chase |
| `locked = FALSE` | Continue to steps 2–4 | Redeem / payment / spend checks |

`wow_drop_player_handoff.py` returns `accountLocked`, `lockReason`, `lockedAt`, `lockReasonComment`, `primaryReason`. **If `primaryReason` is `self_exclusion` or `account_locked`, stop — do not recommend agent contact for Delta recovery.**

### 1. Cohort list (who dropped)

```bash
python wow_drop_analysis/monday_skip_export.py
```

Edit `THIS` / `PRIOR` dates at top of script, or parameterize before run.  
Output: `VIP\Elite_Cursor\WoW Drop Analysis\monday_skip_YYYY-MM-DD.csv` (AID, name, email, account manager, Delta).

**Always show top 10 by Delta** in chat before deep dive.

### 2. Player handoff metrics

```bash
python wow_drop_analysis/wow_drop_player_handoff.py --aid AID --date YYYY-MM-DD
```

Output JSON: `wow_drop_analysis/handoffs/YYYY-MM-DD_AID_handoff.json`

Pulls: **account lock fields first**, then lifetime Purchased, Total Redeemed (+ date), Hold %, Bonuses %, Purchased 7/14/30d, weekday breakdown, pending redeem ID/amount, failed order count, Sunday NGR if day before report is Sunday.

### 3. Validate Delta (single AID)

Reconcile KPI `purchased` vs succeeded `payment_payment_orders` on both weekdays. Check `created` (failed) orders on report date.

### 4. Redemption deep dive

| Source | Use |
|--------|-----|
| `payment_withdraw_money_requests` | Pending amount, redeem ID, recent attempts, confirmed lifetime total |
| `payment_payment_orders` | Failed purchase attempts (`status = created`) |
| KPI daily | Sunday big win (NGR < -5000), rest-of-week purchased |

Do **not** use `redeems_with_balances` alone for pending amount — use `payment_withdraw_money_requests`.

### 5. Agent handoff canvas

Read `.cursor/skills-cursor/canvas/SKILL.md`. Create/update canvas at:

`~/.cursor/projects/<workspace>/canvases/{agent}-{player}-handoff.canvas.tsx`

Copy layout from `wow_drop_analysis/handoffs/wow-drop-handoff.template.canvas.tsx` if present, or last handoff canvas. Fill `DATA` from handoff JSON.

**Canvas structure (compact):**

1. Title: `{Weekday} WoW Drop Reason`
2. Subtitle: `{Name} | AID | email | For {Agent}`
3. **Account lock bar** (if `locked`): reason, `locked_at`, comment — **above** redeem bar
4. Pending redeem bar (light highlight): amount, redeem ID, submitted datetime — only if not self-excluded
5. **Player Metrics** card: Lifetime Purchased | Total Redeemed, date | Hold % | Bonuses % | Purchased 7/14/30d
6. **{Weekday} Purchased WoW Drop** card: Drop Amount (prior vs this weekday) + 3 purchased stats + failed orders note
7. Context tables: day-before big win (if NGR win), recent redeem attempts
8. **Action For {Agent}**: single line — review redeem ID (amount), resolve pending redeem today

**Export:** PNG to `wow_drop_analysis/handoffs/YYYY-MM-DD_AID_handoff.png`

## Reason buckets (investigation — priority order)

| Priority | Signal | Likely reason |
|----------|--------|----------------|
| **1** | `locked = TRUE`, `lock_reason = Exclusion` | **Self-exclusion** |
| **2** | `locked = TRUE` | Account locked |
| **3** | `pre_authorized` redeem + purchased $0 report day | Redemption in progress |
| **4** | NGR < -5000 day before + redeem attempts | Big win, cash out |
| **5** | `created` orders, no succeeded | Payment blocked / failed |
| **6** | Purchased rest of week > 0, report weekday $0 | **Same-weekday skip** (not churn) |

## Do not

- Jump to spend softening, churn, or same-weekday skip **before** account status check
- Recommend agent outreach when `lock_reason = Exclusion` or account locked
- Trust `status = default` alone — always read `locked` + `lock_reason`
- Conflate Monday skip with churn or Active decliner WoW
- Show `bw_pending_redeem_review` in agent handoff (internal only)
- Use em dashes in handoff prose; use `|` or commas
- Omit top 10 Delta when reporting cohort drops

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.
