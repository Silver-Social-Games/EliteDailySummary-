# Elite — Data Definition & Query Guide

**Project:** `silver-social-games-data` (EU)  
**Last updated:** 2026-06-11  
**Project root:** `c:\Users\Owner\Downloads\Elite`  
**Definitions source:** [`decline_check/defination_v2.docx`](decline_check/defination_v2.docx) (OneDrive: `Desktop\VIP\Cursor\defination v2 (1).docx`)

---

## Terminology & fields

| Term | Meaning |
|------|---------|
| **AID** | `account_id` — always show as **AID** in reports |
| **Orders** | = **Purchases** — individual payment transactions in `transactional_data.payment_payment_orders` (`status = 'succeeded'`, `refunded = false`) |
| **Bought** | = **purchased** — KPI column `purchased` from `daily_player_revenue_kpis` (`purchased > 0` on that calendar day, account-level after KPI agg) |
| **Purchased players** | Distinct Elite with **purchased > 0** on that calendar day (not players with only $0 KPI rows). Do **not** say "Players who purchased" or "Buyers" — use **Purchased players** or **purchasers**. |
| **Overall** | All players — platform purchase revenue from `day_kpi` with **no** Elite filter. Pair with **Elite** when reporting "overall yesterday and Elite". |
| **Purchasers** | Same as **Purchased players** — distinct Elite who bought that day |
| **Day compare (mandatory)** | Always **same weekday WoW**: report date vs **7 calendar days earlier** (Tuesday vs last Tuesday, Monday vs last Monday). Never compare consecutive calendar days for the headline day table. |
| **Same-weekday skip** | Bought on **prior same weekday**, **$0 purchased on report day** — still active elsewhere in the week. Use timed weekday offers; **not** churn. Replaces legacy label "weekday timing shift". |
| **Column order (mandatory)** | In compare tables, always **this day / this week first**, **prior day / prior week second**, then change or drop. In **player-level** tables, **Agent** column first (then AID, Name, metrics). |
| **Churn** | Elite with **no purchase in the last 7 calendar days** (inclusive, ending report date). |
| **Active decliner** | Elite who **still purchased in the last 7 days** but bought **less than the prior 7-day week** (`this_week < prior_week`, and `prior_week > 0`). Week-over-week spend decline — **not** churn. |
| **Week windows** | `this_week` = report_date − 6 days … report_date; `prior_week` = report_date − 13 … report_date − 7. |
| **Agent** | Use `tag_agent_1` from `dbt_utils.elite_account_tags` (source of truth). Do **not** use `elite_users.agent_name` alone — it can disagree (e.g. display name vs tag). |
| **Redemption in progress** | Open withdraw: `payment_withdraw_money_requests.status IN ('pre_authorized', 'locked')` **and** amount > 0 (Escalation **Pending Redeem**). Do **not** classify from workflow status alone. |
| **Redemption workflow status** | `elite_users.redeem_status` / `uam_accounts.status` — display context **only when** a pending redeem exists; may lag after redeem completes |
| **`bw_pending_redeem_review`** | Workflow status meaning redeem is under Ops review — **not** sufficient alone for **Redemption in progress**; require `pre_authorized` withdraw |
| **Redemption submitted date** | Latest `DATE(created_at)` from `dbt_sensai_mart.redeems_with_balances` per AID (last redeem request on file; may be confirmed/cancelled) |

### Account status check (mandatory — before drop-reason conclusions)

**Always query `uam_accounts` first** when explaining why a player did not purchase. `status = default` does **not** mean the account is active — check `locked` and `lock_reason`. For **daily summary classification**, treat the account as locked when **`uam_accounts.locked` OR `elite_users.locked`** on the report snapshot (dashboard / Escalation parity when UAM lags).

| Field | Source | Use |
|-------|--------|-----|
| `locked` | `uam_accounts.locked` **OR** `elite_users.locked` | `TRUE` = player blocked from site |
| `lock_reason` | `uam_accounts.lock_reason`, else `elite_users.lock_reason` | e.g. **`Exclusion`** = self-exclusion |
| `locked_at` | `uam_accounts.locked_at` | When lock started — often aligns with last purchase |
| `lock_reason_comment` | `uam_accounts.lock_reason_comment`, else `elite_users.lock_reason_comment` | Ticket / player note (e.g. Zendesk #) |
| `status` | `uam_accounts.status` | Redeem workflow only — **not** a substitute for `locked` |

```sql
SELECT id AS AID, locked, locked_at, lock_reason, lock_reason_comment, status AS redeem_workflow_status
FROM `silver-social-games-data.transactional_data.uam_accounts`
WHERE id = @aid
```

| `locked` | `lock_reason` | Meaning | Agent action |
|----------|---------------|---------|--------------|
| `TRUE` | `Exclusion` | **Self-exclusion** — player removed themselves from site | **Ops / Compliance** — do not retention outreach |
| `TRUE` | other | Account locked (fraud, compliance, etc.) | **Ops** — not retention queue |
| `FALSE` | — | Proceed to redeem / purchase / spend-softening checks | Agent per playbook |

**Rule:** If `locked = TRUE` on or before report date, that is the **primary drop reason**. Do not classify as spend softening, churn outreach, or same-weekday skip until account status is cleared.

### Churn SQL

```sql
-- report_date = e.g. DATE '2026-06-01'
-- Churn: SUM(purchased) from report_date-6 to report_date = 0
bought_last_7_days = 0 OR bought_last_7_days IS NULL
```

### Active decliner SQL (not churn)

```sql
-- report_date = e.g. DATE '2026-06-01'
bought_this_week = SUM(purchased) WHERE date BETWEEN report_date - 6 AND report_date
bought_prior_week = SUM(purchased) WHERE date BETWEEN report_date - 13 AND report_date - 7

-- Active decliner (all required):
bought_this_week > 0
AND bought_prior_week > 0
AND bought_this_week < bought_prior_week
```

### Primary decline reasons (daily summary)

**What it is:** For Elite who **bought in both** rolling 7-day windows but **spent less this week** (`this_week < prior_week`, both > 0), assign **one primary reason** per player. The summary table groups those players by reason and sums their WoW purchase gap (`prior_week − this_week`).

**Not the same as:** Monday skip analysis, churn, or the headline **Purchased players** day count.

**Priority order** (first match wins — implemented in `generate_daily_elite_summary.py`):

| Priority | `primary_reason` | Rule |
|----------|------------------|------|
| 1 | `redemption_in_progress` | Open withdraw `pre_authorized` or `locked`, amount > 0 |
| 2 | `big_win_last_7d` | NGR (7d) ≥ **$5,000** (player up — house lost) |
| 3 | `big_loss_last_7d` | NGR (7d) ≤ **−$5,000** (player down — house won) |
| 4 | `same_weekday_skip` | **Same-weekday skip** — $0 on report day but **did purchase** on prior same weekday (e.g. bought last Tuesday, skipped this Tuesday) |
| 5 | `account_locked` | `uam_accounts.locked` OR `elite_users.locked` on report snapshot |
| 6 | `red_flag` | `elite_users.red_flag` = 1 |
| 7 | `general_spend_softening` | Everything else in the cohort |

```sql
-- Cohort + reason (simplified from generate_daily_elite_summary.py)
CASE
  WHEN COALESCE(pending_redeem.amount, 0) > 0
    THEN 'redemption_in_progress'
  WHEN ngr_7d >= 5000 THEN 'big_win_last_7d'
  WHEN ngr_7d <= -5000 THEN 'big_loss_last_7d'
  WHEN day_this = 0 AND day_prior_week > 0 THEN 'same_weekday_skip'
  WHEN locked THEN 'account_locked'
  WHEN red_flag = 1 THEN 'red_flag'
  ELSE 'general_spend_softening'
END AS primary_reason
```

**Table columns:** `Players` = count in that reason bucket · `$ drop` = sum of WoW purchase gaps · `Avg NGR 7d` / `Avg bonus 7d` = cohort averages for context.

**Top 10 Reason column** (same-day comparison table): auto case summary per AID from batched BigQuery enrich — **Last Purchase 30D**, **Last Play 14D**, redeem workflow, failed orders, and top 3 **Zendesk 14D** ticket subjects (restriction/legal/suspend/unrestrict prioritized over promo). When account is **restricted or suspended** (lock reason, legal action, or Zendesk), Reason opens with a short **Account Restricted - Legal Action** / **Account Suspended** line before activity detail.

**Inactive / suspicious — Zendesk drill-down:** When a player is offline, churned, restricted, redeem-stuck, **skipped purchase days (same-weekday skip)**, or Reason feels incomplete, always check Zendesk beyond auto subjects: read `zendesk.ticket` **description + tags** for the AID (e.g. `kyc_follow_up`, `verification`, `ops_escalation_address_query`, suspend/unrestrict). Confirm rhythm skip vs account block before any purchase push. Ticket body often states the **missing document** (POA declined → valid utility bill or acceptable POA still awaited). Escalate Compliance/Ops with that item; no purchase ask until cleared. Reference: Richard AID 57064501, ticket #589038.

### WoW purchase decline by agent (daily summary)

**What it is:** Same WoW-decline cohort as primary reasons, rolled up by **`tag_agent_1`** (agent on the Elite book).

| Column | Meaning |
|--------|---------|
| **Agent** | `tag_agent_1` from `dbt_utils.elite_account_tags` |
| **Players** | Count of cohort players on that agent |
| **WoW $ drop** | `SUM(prior_week_purchased − this_week_purchased)` for those players |

**Use:** Shows which agent books carry the largest **purchase WoW gap** — not daily revenue, not purchaser count on report day. A high **WoW $ drop** means that agent's declining spenders lost more purchased volume vs their prior 7d week.

---

## Business glossary (definitions v2)

General business and data definitions. For **Elite managed-book reporting** (churn, decliners, daily summary), use **Terminology & fields** above.

### Identity & currencies

| Term | Definition |
|------|------------|
| **Account id / AID** | Player identifier 1:1 — always show as **AID** in reports |
| **uuid** | CRM identifier (`hash/account_id`) for Bloomreach campaigns — required for CRM-facing outputs |
| **Sweep coin (SC)** | Main currency; redeemable — primary currency for analysis |
| **Gold coin (GC)** | Virtual currency; not redeemable |

### Player lifecycle

| Term | Definition |
|------|------------|
| **FTP** | First time purchase |
| **Is FTP / is funded** | Player ever purchased (not registration-only) |
| **Seniority** | Period from FTP to current date. Buckets: First Day, First 2-7d, First 8-30d, First 31-90d, First 91-180d, First 181-365d, +1Y |

### Gaming economics

| Term | Definition |
|------|------------|
| **Bets / stakes / wagers** | Money player puts into the game (`profit` in KPIs) |
| **Payout / wins** | Money returned from game after round (`loss` in KPIs) |
| **GGR / house profit** | Bets − payout = `profit - loss` (SC: **SC_GGR**) |
| **Margin** | GGR / Bets |
| **RTP** | 1 − Margin |
| **NGR** | GGR − Rewards = `profit - loss - sc_reward_amount` — net revenue from gaming perspective |
| **Entertainment rate** | Ratio of bets to (rewards + purchase), SC only. Target **>3×**; **~1×** often indicates abuse |

### Purchase & redeem economics

| Term | Definition |
|------|------------|
| **Purchase** | Money player pays to receive coins |
| **Orders** | = **Purchases** — count or list of succeeded payment orders (`payment_payment_orders`) |
| **Bought** | = **purchased** — KPI measure `purchased` (`purchased > 0` after account-level agg); use **Bought** in Elite reports |
| **Redeem** | Amount player cashes out to bank |
| **Rewards / bonuses** | Extra SC on top of purchase (e.g. pay $100, receive $110 SC → $10 reward) |
| **Net Purchase** | Purchase − paid redeem − chargeback − refund |
| **Net Purchase (alt)** | Purchase − (requested redeem − cancelled redeem) − chargeback − refund |
| **Cancelled redeem** | Redeem cancelled within first 24h before lock |
| **Hold** | Net purchase / purchased — share kept in ecosystem vs money in |
| **Reward Offer %** | SC reward as % of purchase amount |
| **Max value** | Max cumulative revenue to any day in player life (peak LTV). Survives big wins/redeems that flatten lifetime net purchase. Applies to NGR and Net Purchase |

### Rewards domain

| Term | Definition |
|------|------------|
| **Offer code** | Identifies campaign |
| **Purchase rewards** | Delta between purchase price and total SC received (e.g. $19.99 → $24.99) |
| **Non-purchase rewards** | Daily login, free spins, quest rewards — not tied to a purchase |

**Purchase reward types:**

| Type | Notes |
|------|-------|
| **Daily Campaign** (daily special) | CRM daily limited offers by segment; up to ~50% on purchase; often keyed off max historical purchase |
| **Daily Deal** | Limited daily offer by segment; `'dd'` in offer/campaign code |
| **Store offers** | Always available; low offer % (1–2%). High-risk abusers get reduced store |
| **Chain offers** | Sequential steps; `'ch'` / `'chain'` in code. Non-purchase chain rewards exist (e.g. free spins between steps). **Data issue:** purchase with no reward + later chain claim can inflate reward amount |
| **Conversion boosts** | For non-FTP registrants; low amounts ($0.99, $2.99) for long-tail conversion |

**Other reward types:**

| Type | Notes |
|------|-------|
| **Coinback** | Elite cashback as % of NGR (capped); 1–2×/week; campaign name `coinback` |
| **Free spins (FS)** | Per-spin reward rows → inflates reward **count** if FS included |
| **AMOE** | Mail-in Sweeps Coins (~$4/envelope; player cost ~$1–2); periodic cycles |

**Operational notes:**

- FTP usually high conversion offer; then up to **6 first offers** (also elevated vs regular store).
- High-risk players: separate coin store, lower offer %, excluded from daily deal/campaign/chain.
- Many offers keyed off **max historical purchase** and current state.
- Non-store offers often configured midday UTC for US local time → multiple offer codes same UTC day.

---

## Player value segment

**Not the same as Elite managed book.** Value segment **#6 "Elite"** = high predicted/max net purchase tier. **Elite managed book** = `category = 'Elite'` + assigned agent (`tag_agent_1`). Most managed Elite are in segment 6, but segment 6 includes strong non-managed players too.

### How segment is assigned

- Recalculated **every morning** in the data cycle.
- **≤180 days from FTP:** predicted total net purchase for first 180 days → threshold buckets.
- **>180 days from FTP:** **max value net purchase** → same thresholds.
- Promotions use **latest segment** (can change daily).
- **No segment:** new FTP on first purchase day (cycle not run yet); registration-only players.

### Segment thresholds

| # | Name | Threshold | Notes |
|---|------|-----------|-------|
| 0 | Negative | ≤ $0 | Manually corrected for massive winners; high abuser share |
| 1 | Low | ≤ $9.99 | |
| 2 | Low Mid | ≤ $29.98 | |
| 3 | Mid | ≤ $297.35 | |
| 4 | HV Potential | ≤ $654.30 | |
| 5 | HV Potential | ≤ $3,524.20 | |
| 6 | Elite | > $3,524.20 | High-value tier — not exclusive to managed Elite book |

### Table & fields

`silver-social-games-data.patrianna_view.last_user_segment_v`

| Field | Meaning |
|-------|---------|
| `last_user_segment` | Segment name |
| `last_user_segment_org_number` | Segment # (0–6) |
| `last_orig_user_segment` / `_org_number` | Pre-adjustment segment (big-winner corrections use **last** fields) |
| `is_from_model` | 1 = prediction flow (≤180d FTP); 0 = max value (>180d) |
| `test_group` | A/B test group |

```sql
SELECT
  account_id,
  IFNULL(last_user_segment, 'No Segment') AS LastValueSegmentName,
  IFNULL(last_user_segment_org_number, -999) AS LastValueSegmentNumber,
  IFNULL(is_from_model, -999) AS IsValueSegmentFromModel,
  IFNULL(test_group, 'UD') AS ValueSegmentTestGroup
FROM `silver-social-games-data.patrianna_view.last_user_segment_v`
```

---

## Example SQL snippets (definitions v2)

Reusable patterns from the definitions doc. Full enterprise queries: [Daily Agg Per Player](#daily-agg-per-player-query-v1), [Rewards Tableau Extract](#rewards-tableau-extract-28-5-26-v1).

### FTP & registration

```sql
, ftp AS (
  SELECT
    account_id,
    MAX(ftp_date) AS ftp_date,
    MAX(DATE(reg_date)) AS reg_date,
    reg_state,
    unified_channel
  FROM `silver-social-games-data.dbt_marketing_mart.player_stats_daily`
  GROUP BY account_id, reg_state, unified_channel
)
```

### Player details (PII)

```sql
SELECT DISTINCT
  ua.id AS account_id,
  ua.internal AS test_user,
  ua.locked, ua.locked_at, ua.lock_reason, ua.lock_reason_comment,
  ua.phone_number, ua.email,
  ua.status AS redeem_status,
  COALESCE(CONCAT(p.first_name, ' ', p.last_name), ua.name) AS name,
  p.first_name, p.last_name,
  STRING_AGG(CONCAT(hash, '/', ua.id)) AS uuid,
  KYC
FROM `transactional_data.uam_accounts` ua
LEFT JOIN `transactional_data.uam_persons` p ON ua.person_id = p.id
GROUP BY ALL
```

### Promo / campaign classification

```sql
CASE
  WHEN CONTAINS_SUBSTR(campaign, 'chain') OR CONTAINS_SUBSTR(campaign, 'Chain')
    OR CONTAINS_SUBSTR(campaign, 'ch_') THEN 'Chain Offer'
  WHEN CONTAINS_SUBSTR(campaign, 'quest_') THEN 'Quest Rewards'
  WHEN CONTAINS_SUBSTR(campaign, '_hr') THEN 'High Risk'
  WHEN CONTAINS_SUBSTR(campaign, 'vip') THEN 'VIP Offer'
  WHEN CONTAINS_SUBSTR(LOWER(campaign), 'wh') THEN 'Wheel Offer'
  WHEN CONTAINS_SUBSTR(campaign, 'dd') THEN 'Daily Deal'
  WHEN CONTAINS_SUBSTR(campaign, 'conv') AND CONTAINS_SUBSTR(campaign, 'boost') THEN 'Conversion boost'
  WHEN CONTAINS_SUBSTR(LOWER(campaign), 'jan') AND NOT CONTAINS_SUBSTR(LOWER(campaign), 'conv') THEN 'Daily Campaign'
  -- ... feb through dec same pattern ...
  WHEN CONTAINS_SUBSTR(campaign, '1st') AND NOT CONTAINS_SUBSTR(campaign, 'po') THEN 'Conv 1st offer'
  -- ... 2nd through 6th conv offers ...
  ELSE 'Other'
END
```

Full month list and `po 1st`–`po 6th` branches: see [`decline_check/defination_v2.docx`](decline_check/defination_v2.docx) or promo CASE in enterprise SQL files.

### Daily KPI agg per player (core measures)

From `jackpota_agg.daily_player_revenue_kpis` — always `GROUP BY account_id, date` first:

| Measure | SQL (summed) |
|---------|----------------|
| NGR | `SUM(IFNULL(profit,0) - IFNULL(loss,0) - IFNULL(sc_reward_amount,0))` |
| purchased | `SUM(COALESCE(purchased,0))` |
| net_purchases | `SUM(purchased - redeemed - chargeback - refunds)` |
| Bets / Payout | `SUM(profit)` / `SUM(loss)` |
| SC_GGR | `SUM(profit) - SUM(loss)` |
| sc_reward_amount | `SUM(sc_reward_amount)` |
| APD flags | Distinct days with purchase / redeem / spins / rewards > 0 |

---

## Who counts as Elite (managed book)

**Elite accounts with an assigned agent only.** (Do not say “VIP” in reports — use **Elite**.)

| Include | Exclude |
|---------|---------|
| `category = 'Elite'` **and** agent tag present | Elite with **no** agent (`tag_agent_1` / `JSON_VALUE(tags, '$[0]')` is null) |
| ~**2,028** accounts (latest snapshot) | ~**513** Elite without agent (~**2,541** Elite total in source) |

**Do not use** `dbt_aninditac.vip_account_ids` or “all Elite” unless explicitly overridden.

### Source SQL (BigQuery console)

```sql
SELECT DISTINCT
  account_id,
  JSON_VALUE(tags, '$[0]') AS tagAgent1
FROM `silver-social-games-data.transactional_data.uam_account_category_tags`
WHERE category = 'Elite'
  AND JSON_VALUE(tags, '$[0]') IS NOT NULL
```

### Cursor MCP (≤1 GB scan cap)

Use latest snapshot from `dbt_utils.elite_account_tags`:

```sql
WITH latest AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `silver-social-games-data.dbt_utils.elite_account_tags`
)
SELECT DISTINCT
  e.account_id,
  e.tag_agent_1 AS tagAgent1
FROM `silver-social-games-data.dbt_utils.elite_account_tags` e
CROSS JOIN latest l
WHERE e.snapshot_date = l.snap
  AND e.category = 'Elite'
  AND e.tag_agent_1 IS NOT NULL
```

**MCP note:** Filtering `uam_account_category_tags` with `JSON_VALUE` often exceeds the **1 GB** cap (~1.55 GB). Use the mart above in Cursor; use source SQL in the BigQuery UI when you need exact parity.

### Agent roster (latest snapshot example)

| tagAgent1 | Accounts |
|-----------|----------:|
| coral_s | 612 |
| lee_t | 558 |
| gabriel_e | 416 |
| rachel_a | 415 |
| alon_tish | 27 |

---

## Revenue & purchaser metrics

### Yesterday Performance dashboard (Tableau) — **use this for revenue KPIs**

The **Yst Performance** / **Yesterday Performance** Tableau dashboard uses:

| Layer | Table / rule |
|-------|----------------|
| **Elite book** | `dbt_aninditac.elite` — Elite tag **and** Zendesk Silver-agent managed (same as `Current_VIP` + `ZendeskAttributesVIP` in enterprise SQL) |
| **Revenue metric** | `SUM(purchased)` from `jackpota_agg.daily_player_revenue_kpis` on `date = report_date` |
| **Agent in reports** | `tag_agent_1` from `dbt_utils.elite_account_tags` (join for labels; dashboard uses `agent_name` from `dbt_aninditac.elite`) |

**Validated Mon 2026-06-08:** **$146,913.55** revenue · **532** purchasers · book **2,326** (KPI = payments).

| Book definition | Mon 6/8 revenue | Purchasers | Notes |
|-----------------|----------------:|-----------:|-------|
| **`dbt_aninditac.elite` (dashboard)** | **$146,913.55** | **532** | **~146.9K** — Tableau Yst Performance |
| `elite_account_tags` only (latest snap) | $147,982.43 | 535 | +8 accounts not in Zendesk-managed elite (~$1,069 higher) |

Daily summary script and chat KPIs should use **`dbt_aninditac.elite`** unless you explicitly need tag-mart-only counts.

### Tables

| Purpose | Table |
|---------|--------|
| Daily purchases (revenue) | `jackpota_agg.daily_player_revenue_kpis` — column `purchased`, filter `date` |
| Reconciliation | `transactional_data.payment_payment_orders` — `status = 'succeeded'`, `refunded = false` |
| **Elite book (dashboard / revenue)** | **`dbt_aninditac.elite`** |
| Elite tags / agent (`tag_agent_1`) | `dbt_utils.elite_account_tags` (latest `snapshot_date`) |

### Critical rule: KPI grain (mandatory)

`daily_player_revenue_kpis` has **multiple rows per account per day** (brand, `bonus_type`, country, etc.).

**Always aggregate account-first** — never `SUM(purchased)` or `COUNT(DISTINCT account_id)` directly on the raw table.

| Mistake | Result |
|---------|--------|
| `SUM(purchased)` on raw KPI rows | **Wrong revenue** — can under-count (partial loads) or over-count (multi-row grain). Wed 2026-06-10: raw scan ~$252K / $60K Elite vs correct **$725K / $180K** after `GROUP BY account_id, date`. |
| `COUNT(DISTINCT account_id)` without `purchased > 0` | Counts **active** players, not **purchasers** (e.g. 1,070 vs 445) |
| `COUNT(DISTINCT account_id)` on raw rows with `purchased > 0` | **Wrong purchaser count** — same multi-row grain issue |

**Always:**

1. `GROUP BY account_id, date` and `SUM(purchased)` first into `day_kpi`
2. Then `SUM(purchased)` for revenue and `COUNT(DISTINCT CASE WHEN purchased > 0 THEN account_id END)` for purchasers
3. Reconcile Elite to `payment_payment_orders` when validating

**Data completeness:** KPI partitions for **yesterday** may still be loading early morning. If revenue looks like a sharp ~70% drop vs prior same weekday, **re-run** after the daily ETL (or after 11:00 AM summary) before reporting.

### Overall vs Elite revenue (canonical)

| Segment | Book filter | Use |
|---------|-------------|-----|
| **Overall** | All accounts in `day_kpi` | Platform purchase revenue — "overall yesterday" |
| **Elite** | `dbt_aninditac.elite` | Yesterday Performance dashboard parity |

**Daily summary** (`generate_daily_elite_summary.py`) writes both to `decline_check/daily_summaries/YYYY-MM-DD_elite_daily_summary.md` — use that file for chat KPIs; do not scan raw KPI without account-level agg.

```sql
-- report_date = yesterday, e.g. DATE '2026-06-10'
WITH day_kpi AS (
  SELECT
    account_id,
    SUM(CAST(purchased AS FLOAT64)) AS purchased
  FROM `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis`
  WHERE date = DATE '2026-06-10'  -- report_date
  GROUP BY account_id
),
elite_accounts AS (
  SELECT DISTINCT account_id
  FROM `silver-social-games-data.dbt_aninditac.elite`
)
SELECT
  DATE '2026-06-10' AS report_date,
  ROUND(SUM(k.purchased), 2) AS overall_revenue_usd,
  COUNT(DISTINCT CASE WHEN k.purchased > 0 THEN k.account_id END) AS overall_purchased_players,
  ROUND(SUM(IF(e.account_id IS NOT NULL, k.purchased, 0)), 2) AS elite_revenue_usd,
  COUNT(DISTINCT CASE WHEN e.account_id IS NOT NULL AND k.purchased > 0 THEN k.account_id END)
    AS elite_purchased_players
FROM day_kpi k
LEFT JOIN elite_accounts e ON k.account_id = e.account_id;
```

**Validated Wed 2026-06-10:** overall **$725,259.65** · **5,661** purchasers · Elite **$180,293.62** · **611** purchased players · Elite share **24.9%**.

### Daily Elite revenue only (Yesterday Performance aligned)

```sql
-- report_date = yesterday — Elite slice of day_kpi above
WITH elite_accounts AS (
  SELECT DISTINCT account_id
  FROM `silver-social-games-data.dbt_aninditac.elite`
),
day_kpi AS (
  SELECT
    account_id,
    SUM(CAST(purchased AS FLOAT64)) AS purchased
  FROM `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis`
  WHERE date = DATE '2026-06-08'  -- report_date
  GROUP BY account_id
)
SELECT
  DATE '2026-06-08' AS report_date,
  ROUND(SUM(d.purchased), 2) AS elite_revenue_usd,
  COUNT(DISTINCT CASE WHEN d.purchased > 0 THEN d.account_id END) AS players_who_purchased,
  (SELECT COUNT(*) FROM elite_accounts) AS elite_accounts_in_book
FROM day_kpi d
INNER JOIN elite_accounts e USING (account_id);
```

### Payment reconciliation

```sql
-- Same elite_accounts CTE and report_date
SELECT
  COUNT(DISTINCT p.account_id) AS elite_purchasers,
  COUNT(*) AS order_count,
  ROUND(SUM(p.amount), 2) AS elite_revenue_usd
FROM `silver-social-games-data.transactional_data.payment_payment_orders` p
INNER JOIN elite_accounts e ON p.account_id = e.account_id
WHERE DATE(p.created_at) = DATE '2026-06-08'
  AND p.status = 'succeeded'
  AND COALESCE(p.refunded, FALSE) = FALSE;
```

### Tag-mart-only book (higher than dashboard — do not use for Yst Performance)

```sql
-- ~$1k higher than dashboard on 2026-06-08; 8 extra purchasers
WITH latest AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `silver-social-games-data.dbt_utils.elite_account_tags`
)
SELECT DISTINCT account_id
FROM `silver-social-games-data.dbt_utils.elite_account_tags` e
CROSS JOIN latest l
WHERE e.snapshot_date = l.snap
  AND e.category = 'Elite'
  AND e.tag_agent_1 IS NOT NULL
```

Purchaser count and revenue **must match** between KPI (after account-level agg + `purchased > 0`) and payments.

### Revenue by agent

```sql
-- Add tag_agent_1 to vip_accounts CTE, join day_kpi, GROUP BY tagAgent1
```

---

## Reference example — 2026-06-01 (yesterday)

| Metric | Value |
|--------|------:|
| VIP purchase revenue | **$126,595.72** |
| VIP purchasers | **445** |
| Payment orders | 1,428 |
| VIP accounts in book | 2,028 |
| Prior day revenue (2026-05-31) | $130,543.47 (−3.0% DoD) |

---

## Monday benchmark — yesterday vs prior 3 Mondays

**Default cadence:** Compare **yesterday** to the **3 prior Mondays** (same VIP definition). Dates in the warehouse are calendar dates (ET reporting).

### Multi-Monday SQL template

```sql
-- Set dates: yesterday + 3 prior Mondays (adjust as needed)
WITH latest AS (
  SELECT MAX(snapshot_date) AS snap
  FROM `silver-social-games-data.dbt_utils.elite_account_tags`
),
vip_accounts AS (
  SELECT DISTINCT e.account_id
  FROM `silver-social-games-data.dbt_utils.elite_account_tags` e
  CROSS JOIN latest l
  WHERE e.snapshot_date = l.snap
    AND e.category = 'Elite'
    AND e.tag_agent_1 IS NOT NULL
),
dates AS (
  SELECT report_date FROM UNNEST([
    DATE_SUB(CURRENT_DATE('America/New_York'), INTERVAL 1 DAY),  -- yesterday
    -- add 3 prior Mondays explicitly or generate via calendar table
    DATE '2026-05-25', DATE '2026-05-18', DATE '2026-05-11'
  ]) AS report_date
  WHERE EXTRACT(DAYOFWEEK FROM report_date) = 2  -- Monday in BQ (1=Sun, 2=Mon)
),
day_kpi AS (
  SELECT
    k.date AS report_date,
    k.account_id,
    SUM(CAST(k.purchased AS FLOAT64)) AS purchased
  FROM `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis` k
  INNER JOIN vip_accounts v ON k.account_id = v.account_id
  INNER JOIN dates d ON k.date = d.report_date
  GROUP BY 1, 2
)
SELECT
  report_date,
  FORMAT_DATE('%A', report_date) AS day_name,
  ROUND(SUM(purchased), 2) AS vip_revenue_usd,
  COUNT(DISTINCT CASE WHEN purchased > 0 THEN account_id END) AS vip_players_who_purchased,
  ROUND(SUM(purchased) / NULLIF(COUNT(DISTINCT CASE WHEN purchased > 0 THEN account_id END), 0), 2) AS revenue_per_purchaser
FROM day_kpi
GROUP BY 1, 2
ORDER BY report_date DESC;
```

### Saved snapshot — 2026-06-02 run

| Date | Label | VIP revenue | Purchasers | $ / purchaser |
|------|-------|------------:|-----------:|--------------:|
| **2026-06-01** | Yesterday (Mon) | **$126,595.72** | **445** | $284.48 |
| 2026-05-25 | Prior Mon −1 | $116,367.16 | 412 | $282.44 |
| 2026-05-18 | Prior Mon −2 | $127,365.17 | 417 | $305.43 |
| 2026-05-11 | Prior Mon −3 | $149,719.07 | 485 | $308.70 |
| *Avg prior 3 Mondays* | | *$131,150.47* | *438* | *$298.86* |

**Yesterday vs prior 3 Monday average:** revenue **−3.5%** (−$4,555); purchasers **+7**.

| vs | Revenue Δ | % | Purchasers Δ |
|----|----------:|--:|-------------:|
| 2026-05-25 | +$10,229 | +8.8% | +33 |
| 2026-05-18 | −$769 | −0.6% | +28 |
| 2026-05-11 | −$23,123 | −15.4% | −40 |

### Active decliners vs churn (2026-06-01 snapshot) — do not confuse

| Segment | Players | Notes |
|---------|--------:|-------|
| **Churn** (no purchase May 26–Jun 1) | **905** | Zero in last 7 days |
| **Active decliners** (WoW: this week < prior week, both > 0) | **458** | Still buying; spending down |
| ↳ Also skipped **this Monday** only | 301 | Calendar Mon miss is a subset, not the definition |
| **2-week decline** (w0 < w1 < w2) | **155** | Deeper pattern |

**Wrong:** Call Monday non-buyers “Active decliners” or call WoW decliners “churn.”  
**Right:** Active decliner = **less purchased than prior week**; Churn = **nothing in 7 days**.

---

## Validation thresholds

| Check | Threshold |
|-------|-----------|
| Day-over-day % change | ±30% WARNING; ±50% ERROR unless explained |
| KPI vs payments revenue | Must reconcile |
| Purchaser count | KPI (`purchased > 0`) = payment distinct accounts |
| Missing partition / date | ERROR |

---

## Daily summary (11:00 AM)

| Item | Path |
|------|------|
| Generator script | `decline_check/generate_daily_elite_summary.py` |
| Output folder | `decline_check/daily_summaries/YYYY-MM-DD_elite_daily_summary.md` |
| Cursor skill | `.cursor/skills/daily-elite-summary/SKILL.md` |
| Schedule (Windows) | `decline_check/register_daily_elite_task.ps1` → daily **11:00 AM** |

Manual: `python decline_check/generate_daily_elite_summary.py` or `@daily-elite-summary` in chat.

---

## Daily Agg Per Player Query v1

**Source (OneDrive):** `Desktop\VIP\Cursor\Daily Agg Per Player Query v1 (1).sql`  
**Project copy:** [`decline_check/Daily_Agg_Per_Player_Query_v1.sql`](decline_check/Daily_Agg_Per_Player_Query_v1.sql)

Enterprise **daily player-level** aggregation for Elite/VIP analytics. Grain: **`account_id` + `date`** (from `jackpota_agg.daily_player_revenue_kpis`), filtered `d.date >= '2025-01-01'` in final output.

### What it builds

| Layer | Purpose |
|-------|---------|
| **`d`** | Daily KPI agg per player: `purchased`, `net_purchases`, `NGR`, `redeemed`, `spins`, `sc_reward_amount`, seniority from FTP, APD flags |
| **`Current_VIP`** | Elite + agent (`category='Elite'`, `tagAgent1` not null) — same rule as this doc |
| **`VIP_hist`** | Historical Elite tags from `dbt_utils.elite_account_tags` + `Is_Currently_VIP` flag |
| **`VIP`** | Current Elite joined to Zendesk agent-managed players |
| **`redeem_his` / `first_redeem`** | Redemption requests from `payment_withdraw_money_requests` |
| **`Churn_Times`** | FTP-based churn/reactivation (default **20 days** since last purchase — differs from **7-day Churn** in this doc) |
| **`DailySegment`** | User value segment (model or lifetime net-purchase tiers) |
| **Final `SELECT`** | Joins limits, flags, balances, lifetime metrics, `IS_VIP_THIS_DAY`, `THIS_DAY_VIP_AGENT`, churn flags |

### Elite definition in query (`Current_VIP`)

```sql
SELECT DISTINCT
  account_id,
  JSON_VALUE(tags, '$[0]') AS tagAgent1
FROM `silver-social-games-data.transactional_data.uam_account_category_tags`
WHERE category = 'Elite'
  AND JSON_VALUE(tags, '$[0]') IS NOT NULL
```

**Cursor MCP:** prefer `dbt_utils.elite_account_tags` (latest snapshot) when `uam_account_category_tags` exceeds scan cap.

### Key output fields (Elite daily summary)

| Field | Meaning |
|-------|---------|
| `account_id` | **AID** |
| `date` | Calendar day |
| `purchased` / `net_purchases` | **Bought** / net after redeem/chargeback/refund |
| `NGR` | `profit - loss - sc_reward_amount` |
| `sc_reward_amount` | Bonus SC (rewards) |
| `IS_VIP_THIS_DAY` | 1 if Elite+agent on that snapshot day (`VIP_hist`) |
| `THIS_DAY_VIP_AGENT` | `hist_tagAgent1` for that day |
| `agent_name` | Zendesk-managed agent (current VIP join) |
| `redeem_status` | Account redeem workflow status (may be stale); show in Reason **only with** pending `pre_authorized` redeem |
| `reason_table` | Top 10 **Reason** column — 1–2 sentence case summary (BigQuery + Zendesk subjects) |
| `favourite_game_7d` | Top game by spins in rolling 7d window (Top 10 column) |
| `days_since_last_purchase` | From `Churn_Times` |
| `is_churn` / `is_churn_today` | Query churn = **20d** since last purchase (not 7d Elite churn) |

### Filter to Elite book only

```sql
-- Append to final WHERE or wrap query:
WHERE d.date = @report_date
  AND IS_VIP_THIS_DAY = 1
  -- or join Current_VIP / latest elite_account_tags
```

### Primary tables

- `jackpota_agg.daily_player_revenue_kpis` — core daily metrics
- `transactional_data.uam_account_category_tags` — Elite tags
- `dbt_utils.elite_account_tags` — VIP history
- `transactional_data.payment_payment_orders` — FTP / purchases
- `transactional_data.payment_withdraw_money_requests` — redeems
- `dbt_dashboards_mart` / `zendesk` — agent contact attributes

### Notes vs this doc

| Topic | Daily Agg query | Elite.MD daily summary |
|-------|-----------------|------------------------|
| Elite label | `VIP` / `IsVIP` in query | **Elite** in reports |
| Churn | 20 days (`churn_period_days`) | **7 days** no purchase |
| Agent | `tagAgent1`, `THIS_DAY_VIP_AGENT`, Zendesk `agent_name` | **`tag_agent_1`** source of truth |
| Date range | `d.date >= '2025-01-01'` (configurable) | Rolling 7d / weekday compare |

Full SQL (~1,280 lines): open [`decline_check/Daily_Agg_Per_Player_Query_v1.sql`](decline_check/Daily_Agg_Per_Player_Query_v1.sql).

---

## Rewards Tableau Extract 28-5-26 v1

**Source (OneDrive):** `Desktop\VIP\Cursor\Rewards Tableau Extract 28-5-26 v1 (1).sql`  
**Project copy:** [`decline_check/Rewards_Tableau_Extract_28-5-26_v1.sql`](decline_check/Rewards_Tableau_Extract_28-5-26_v1.sql)

**Tableau / rewards analytics extract** — one row per **AID + reward_date + product/campaign**, unioning platform rewards and purchase-based “Offer Discount Reward” rows. Final output filtered to **last 180 days** (`HAVING reward_date >= yesterday - 180d`).

### What it builds

| Layer | Purpose |
|-------|---------|
| **`d`** | Daily player context (seniority, reg/ftp, channel, geo) — metrics mostly commented out; used for join attributes |
| **`Current_VIP` / `VIP`** | Elite + agent + Zendesk-managed players (`IsVIP` = Elite book) |
| **`purchases`** | Succeeded offers from `payment_payment_orders` with `sc_reward_amount = GREATEST(sc_amount - amount, 0)` |
| **`Rewards`** | Aggregated from `jackpota_agg.fact_rewards` (excl. `Offer Discount Reward`) |
| **`Rewards_U`** | **UNION ALL** purchases as `product_title = 'Offer Discount Reward'` + platform rewards |
| **`RU1`** | Running `Cumulative_purchases` over reward timeline |
| **`LT` / `MaxValue`** | Lifetime NGR, net purchases, last purchase/redeem/active/rewards dates |
| **Final `SELECT`** | Rewards grain + player flags, balances, VIP attrs, value segment |

### Grain & key fields

| Field | Meaning |
|-------|---------|
| `account_id` | **AID** |
| `reward_date` | Calendar day of reward or purchase |
| `product_title` | Reward product or `'Offer Discount Reward'` for purchases |
| `campaign_title` | Campaign name or `offer_code` for purchases |
| `sc_reward_amount` | SC bonus (rewards table or purchase delta) |
| `gold_reward_amount` | GC bonus |
| `purchase_amount` / `sc_amount` | Populated for Offer Discount rows only |
| `purchase_index_overall` / `purchase_index_daily` | Purchase sequence (LT / within-day) |
| `Cumulative_purchases` | Running purchase count through reward_date |
| `IsVIP` | `'VIP'` if in Elite+agent+Zendesk book (use **Elite** in reports) |
| `agent_name` | From `Current_VIP.tagAgent1` — prefer **`tag_agent_1`** per this doc |

### Elite filter

```sql
-- Tableau / ad-hoc Elite slice:
WHERE IsVIP = 'VIP'
-- or join dbt_utils.elite_account_tags (latest snapshot) for tag_agent_1
```

### Primary tables

- `jackpota_agg.fact_rewards` — platform rewards (SC/GC, product, campaign)
- `transactional_data.payment_payment_orders` — purchases → Offer Discount Reward rows
- `jackpota_agg.daily_player_revenue_kpis` — daily context (`d`)
- `transactional_data.uam_account_category_tags` — Elite tags (`Current_VIP`)
- `zendesk.ticket` / `zendesk.user` — agent-managed VIP join
- `jackpota_agg.fact_account_balance_history` — yesterday SC balances
- `patrianna_view.last_user_segment_v` — value segment

### Notes vs this doc

| Topic | Rewards extract | Elite.MD |
|-------|-----------------|----------|
| Elite label | `IsVIP` / `'VIP'` | **Elite** |
| Bonus 7d | `sc_reward_amount` per reward row | `sc_reward_amount + sc_envelopes_amount` from KPIs |
| Agent | `tagAgent1` + Zendesk `agent_name` | **`tag_agent_1`** source of truth |
| Date window | Last **180 days** | Rolling 7d / report date |
| Purchases | `payment_payment_orders` (`success`) | Also `status = 'succeeded'`, `refunded = false` in reconciles |

Full SQL (~686 lines): open [`decline_check/Rewards_Tableau_Extract_28-5-26_v1.sql`](decline_check/Rewards_Tableau_Extract_28-5-26_v1.sql).

## Related files

- `decline_check/defination_v2.docx` — business glossary, rewards domain, value segments (definitions v2)
- `decline_check/Daily_Agg_Per_Player_Query_v1.sql` — daily player agg (VIP/Elite analytics)
- `decline_check/Rewards_Tableau_Extract_28-5-26_v1.sql` — rewards + purchases Tableau extract
- `decline_check/` — coral_s decline playbook (subset of Elite book)
- `~/.cursor/skills/vip-revenue-daily-check/` — Elite revenue checks (points here)
