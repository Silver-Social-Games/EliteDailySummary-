# Elite — Canonical Data Definitions

**Project:** `silver-social-games-data` (EU)
**Last updated:** 2026-07-28
**Purpose:** Stable Elite terminology, book definitions, metric grain, and
decision logic. Operational commands and schedules belong in each initiative's
documentation and Cursor Skill.

## Contents

1. [Terminology](#terminology)
2. [Elite managed book](#elite-managed-book)
3. [Revenue and Purchased players](#revenue-and-purchased-players)
4. [Account status and decline reasons](#account-status-and-decline-reasons)
5. [Player value segment](#player-value-segment)
6. [Rewards and promotions](#rewards-and-promotions)
7. [Validation](#validation)
8. [Current workflows](#current-workflows)
9. [Reference sources](#reference-sources)

## Terminology

Use these definitions in every Elite report.

| Term | Canonical definition |
|------|----------------------|
| **Elite** | Managed book defined below. Do not say VIP in reports. |
| **AID** | `account_id`; always display it as **AID**. Use for analysis. |
| **uuid** | Same player identity for CRM / Bloomreach campaign exports. Do not confuse with purchase Order ID or Zendesk **TID**. |
| **Order / Purchase** | Individual succeeded, non-refunded payment order from `payment_payment_orders`. |
| **Bought** | KPI `purchased > 0` on an account-day after KPI aggregation. |
| **Purchased players** | Distinct Elite with account-day `purchased > 0`. Do not say Buyers or Players who purchased. |
| **Active player** | AID that made a bet or purchase during the specified period. For a calendar month, aggregate KPI rows by account and date first, then classify as active when monthly `SUM(profit) > 0 OR SUM(purchased) > 0`. |
| **Overall** | All platform accounts after account-day KPI aggregation, without an Elite filter. |
| **Agent** | `tag_agent_1` from the latest `dbt_utils.elite_account_tags` snapshot. |
| **Churn** | No purchase in the last 7 calendar days, inclusive through report date. |
| **Active decliner** | Purchased in the last 7 days and prior 7 days, but less in the latest window. |
| **Same-weekday skip** | Purchased on the prior same weekday and $0 on report day; not automatically Churn. |
| **TID** | Zendesk ticket ID. Use Order ID or transaction UUID for purchases. |

### Calendar and presentation rules

- Compare report date with 7 calendar days earlier for headline day comparisons.
- `this_week` is report date minus 6 days through report date.
- `prior_week` is report date minus 13 through minus 7 days.
- Show this period first, prior period second, then delta.
- Put Agent first in player-level tables, followed by AID and Name.

### Business glossary

| Term | Definition |
|------|------------|
| **FTP** | First time purchase. |
| **Is FTP / funded** | Player has ever purchased; not registration-only. |
| **SC** | Sweep Coin, redeemable and primary for analysis. |
| **GC** | Gold Coin, not redeemable; treat as secondary / virtual. |
| **Bets / wagers / stakes** | KPI `profit` — money the player puts into the game. |
| **Payout / wins** | KPI `loss` — money returned to the player after a round. |
| **GGR** | House profit: `profit - loss` (bets − payout). |
| **NGR** | Gaming net revenue: `profit - loss - sc_reward_amount` (GGR − rewards). |
| **Margin** | GGR divided by Bets. |
| **RTP** | `1 - Margin`. |
| **Purchase (amount)** | Money the player puts into the system to get coins to play. |
| **Redeem** | Amount the player cashes out to their bank account. |
| **Cancelled redeem** | Redeem cancelled within the first 24 hours of the request, before the redeem becomes locked. |
| **Net Purchase** | Canonical: purchase − paid redeem − chargeback − refund. Alternate (requested): purchase − (requested redeem − cancelled redeem) − chargeback − refund. State which variant when not using paid redeem. |
| **Hold** | Net Purchase divided by Purchased — share of money kept in the ecosystem. Higher is better. |
| **Rewards / bonuses** | Extra SC or GC granted beyond the paid amount (e.g. pay $100, receive $110 → $10 reward). |
| **Reward Offer %** | SC reward divided by purchase amount. |
| **Entertainment rate** | SC bets ÷ (SC purchase + SC rewards). Players must wager funds at least once. Ideal is high (>×3); ~×1 is usually an abuse signal (not the only signal). |
| **Seniority** | Days from FTP to the as-of / report date (`DaysFromFTP`). See cohorts below. |
| **Max value** | Peak cumulative NGR or Net Purchase across the player lifetime. Preserves a “good player” tag after big wins that are redeemed and pull lifetime Net Purchase down or negative. |

#### Seniority cohorts

| Days from FTP | Cohort |
|---------------|--------|
| 0 | First Day |
| 1–6 | First 2-7d |
| 7–29 | First 8-30d |
| 30–89 | First 31-90d |
| 90–179 | First 91-180 |
| 180–364 | First 181-365 |
| 365+ | +1Y |
| else / missing FTP | UD |

## Elite managed book

### Dashboard and revenue book

Use `dbt_aninditac.elite` for Yesterday Performance dashboard parity and revenue
reporting. Do not substitute `dbt_aninditac.vip_account_ids` or the tag-only
book unless the analysis explicitly requires it.

### Agent labels and MCP-safe roster

Use the latest `dbt_utils.elite_account_tags` snapshot for `tag_agent_1`.

```sql
WITH latest AS (
  SELECT MAX(snapshot_date) AS snapshot_date
  FROM `silver-social-games-data.dbt_utils.elite_account_tags`
)
SELECT DISTINCT
  e.account_id,
  e.tag_agent_1
FROM `silver-social-games-data.dbt_utils.elite_account_tags` e
JOIN latest l USING (snapshot_date)
WHERE e.category = 'Elite'
  AND e.tag_agent_1 IS NOT NULL
```

Filtering raw `uam_account_category_tags` with `JSON_VALUE` often exceeds the
Cursor MCP 1 GB scan cap. Use the mart above in Cursor. Use the raw source only
in BigQuery when exact source parity is required.

The tag-only roster can contain accounts that are not in the dashboard-managed
book, producing a small revenue variance. Join labels to `dbt_aninditac.elite`;
do not use the roster alone as the revenue-book filter.

## Revenue and Purchased players

### Canonical sources

| Purpose | Source |
|---------|--------|
| Revenue and daily KPIs | `jackpota_agg.daily_player_revenue_kpis` |
| Dashboard Elite book | `dbt_aninditac.elite` |
| Agent labels | Latest `dbt_utils.elite_account_tags` |
| Order reconciliation | `transactional_data.payment_payment_orders` |

### Mandatory KPI grain

`daily_player_revenue_kpis` can contain multiple rows per AID and date. Always
aggregate to `account_id, date` before revenue or player counts.

```sql
WITH day_kpi AS (
  SELECT
    account_id,
    date,
    SUM(CAST(purchased AS FLOAT64)) AS purchased
  FROM `silver-social-games-data.jackpota_agg.daily_player_revenue_kpis`
  WHERE date = @report_date
  GROUP BY account_id, date
)
SELECT
  SUM(purchased) AS revenue,
  COUNTIF(purchased > 0) AS purchased_players
FROM day_kpi
```

Never:

- `SUM(purchased)` directly on raw KPI rows.
- Count all distinct AIDs as Purchased players.
- Use payment orders as the dashboard revenue source.

Use payment orders to reconcile the account-day KPI result:

```sql
WHERE DATE(created_at) = @report_date
  AND status = 'succeeded'
  AND COALESCE(refunded, FALSE) = FALSE
```

If yesterday appears to be an unexplained severe drop, verify partition
completeness and rerun after the scheduled 10:00 AM Israel report before
publishing a conclusion.

## Account status and decline reasons

### Account check is mandatory

Before explaining a purchase drop, query `uam_accounts`. `status = default`
does not mean the account is active.

```sql
SELECT
  id AS AID,
  locked,
  locked_at,
  lock_reason,
  lock_reason_comment,
  status AS redeem_workflow_status
FROM `silver-social-games-data.transactional_data.uam_accounts`
WHERE id = @aid
```

- `locked = TRUE` and `lock_reason = 'Exclusion'`: self-exclusion; no retention
  outreach.
- Other locked account: route to Ops or Compliance, not a purchase chase.
- Unlocked: continue to redeem, payment, activity, and spend checks.

For daily classification, treat the account as locked when
`uam_accounts.locked OR elite_users.locked` on the report snapshot.

### Churn and Active decliner

```sql
-- Churn
COALESCE(bought_last_7_days, 0) = 0

-- Active decliner
bought_this_week > 0
AND bought_prior_week > 0
AND bought_this_week < bought_prior_week
```

### Primary decline reason

Assign one primary reason to Active decliners. First valid match wins:

1. Self-exclusion or account lock. Account safety overrides outreach.
2. Redemption in progress: open withdraw in `pre_authorized` or `locked` with
   amount greater than zero.
3. Big win in last 7 days: `NGR <= -5000` (player won; house NGR is negative).
4. Big loss in last 7 days: `NGR >= 5000` (player lost; house NGR is positive).
5. Same-weekday skip.
6. Red flag.
7. General spend softening.

Do not infer Redemption in progress from workflow status alone. Confirm an open
withdraw in `payment_withdraw_money_requests`.

When a reason remains incomplete, check Zendesk ticket description and tags for
KYC, verification, suspension, restriction, and Ops escalation context. TID is
the Zendesk ticket ID.

## Player value segment

Value segment 6 named Elite is **not** the Elite managed book. Most managed Elite
accounts sit in segment 6, but segment 6 also includes strong non-managed players,
and managed Elite is not limited to segment 6 alone.

- Segment is recalculated each morning for funded players.
- Up to 180 days from FTP: predicted 180-day Net Purchase (thresholds originally
  sized from group-size percentiles).
- After 180 days: max-value Net Purchase, same thresholds.
- Use the **latest** segment for purchase / reward targeting; it can change daily
  as value accumulates.
- No segment on FTP day until the morning cycle runs, or for registration-only
  (never purchased) players.

| Segment | Threshold | Notes |
|---------|-----------|-------|
| 0 Negative | <= $0 | Manually corrected to push massive winners back to their proper segment; often enriched with high-risk abusers. |
| 1 Low | <= $9.99 | |
| 2 Low Mid | <= $29.98 | |
| 3 Mid | <= $297.35 | |
| 4 HV Potential | <= $654.30 | |
| 5 HV Potential | <= $3,524.20 | |
| 6 Elite | > $3,524.20 | Strong players by value; not equivalent to the managed Elite book. |

Source: `patrianna_view.last_user_segment_v` (one row per player).

Use **last_*** (adjusted) segment fields for targeting and reporting, not
**last_orig_***. Orig values are pre-adjustment; last values reflect the manual
correction that keeps big winners in higher segments.

| Column | Meaning |
|--------|---------|
| `last_user_segment` | Adjusted segment name (use this) |
| `last_user_segment_org_number` | Adjusted segment number 0–6 (use this) |
| `last_orig_user_segment` | Pre-adjustment segment name |
| `last_orig_user_segment_org_number` | Pre-adjustment segment number |
| `is_from_model` | Prediction flow (still within first 180 days) vs max-value flow (after 180 days) |
| `test_group` | Value-segment test group when present |

## Rewards and promotions

### How rewards work

- **Offer code** identifies the campaign.
- Rewards are **purchase** (delta between SC received and amount paid) or
  **non-purchase** (login bonus, free spins, quests, envelopes, and similar).
- Non-store purchase campaigns are usually limited in how many times an offer can
  be used. **Store** offers (regular or high-risk) are unlimited.
- Many non-store purchase offers are scheduled around midday UTC for US local
  time, so the same UTC day can show multiple offer-code sets at different hours.
- Purchase offer ranges are often keyed off the player's historical **max
  purchase** and current moment.
- **High-risk** (abuser) players get a high-risk store with lower offer % and are
  excluded from daily deal, daily campaign, chain, and similar non-store rewards
  (`_hr` in campaign code).

### Conversion and early-purchase flows

- **Conversion (conv)** offers target registration → FTP. Codes often contain
  `ftp0` or `conv`, with `1st`…`6th` for days since registration in the first
  week if the player has not purchased. A conversion offer is intended once for
  first purchase; players may skip it and FTP on chain, daily campaign, or store.
- After FTP, players often enter up to **six first purchase offers (po)** that are
  richer than regular store offers. Identify with `po` in the campaign name, or
  with `4th`/`5th`/`6th` **without** `ftp0` (otherwise it is a conv offer).
- **Conversion boost** targets late reg→FTP (often weeks after registration),
  sometimes at atypical small amounts ($0.99 / $2.99 / $4.99). The chosen FTP
  amount steers later purchase-offer ladders.
- **OTP** (one-time purchase, `otp` in code): protocol after ~3 days from FTP if
  there has been no second purchase; usable once.
- **Reactivation** (`reac`): for players with no purchase for over 10 days;
  typically once per cooldown window. After they buy again, they return to regular
  segment / risk offers.

### Purchase reward types

| Type | Notes |
|------|-------|
| Daily Campaign | Also “daily special”; CRM limited offer, often up to ~50%, tailored by segment / max historical purchase. Month tokens or `dc` in code. |
| Daily Deal | Limited daily offer by segment; `dd` in code, or weekday tokens (`sun_`…`sat_`). |
| Store offer | Always available, usually ~1–2% reward. High-risk store is lower %. |
| Chain offer | Sequential unlocks (`ch` / `chain`). May include non-purchase steps (e.g. free spins). Known data issue: a later chain claim can register the prior purchase amount plus delta as “reward,” inflating reward amount. |
| Conversion / conv | Reg→FTP ladder; `ftp0` / `conv` + day ordinals without `po`. |
| Conversion boost | Late FTP push; `conv` + `boost` (and related low-ticket offers). |
| Purchase offer (po) | Post-FTP early purchase ladder; `po` or ordinals without `ftp0`. |
| Reactivation | `reac`; 10+ days without purchase. |
| OTP | `otp`; post-FTP second-purchase nudge. |
| Quest rewards | Mission completion (wager / win / purchase X); `quest_` in code. |
| Wheel / GC / Elite offer | `wh`, GoldCoinOffer / `kgc` / `mgc`, `vip` in code — classify explicitly when analyzing mix. |
| Other | Remaining purchase offers not listed above. |

### Other notable reward types

| Type | Notes |
|------|-------|
| Coinback | Elite cashback as % of NGR with a cap; usually 1–2× per week under campaign name `coinback`. |
| Free spins (FS) | Spins on a slot or slot group (often ~20¢ bet). Each spin is its own reward row — reward **counts** inflate; prefer reward **amount**. |
| AMOE | Mail-in Sweeps Coins; periodic cycles; historically ~$4 SC per envelope vs ~$1–2 player postage cost. Subject to abuse controls. |

Purchase reward is the positive difference between SC received and amount paid.
Non-purchase rewards include login, spins, quests, and envelopes.

### Offer-type classification (first match wins)

Canonical matching order for `offer_code` / campaign (Tableau-style rules from
defination v4). Convert to `CONTAINS_SUBSTR` / `LOWER` in BigQuery as needed.

1. `chain` / `Chain` / `ch_` → Chain Offer
2. `quest_` → Quest Rewards
3. `_hr` → High Risk
4. `vip` → Elite offer (source label may say VIP Offer)
5. `wh` (lower) → Wheel Offer
6. `GoldCoinOffer` or `kgc` at position 4–5 or `mgc` → Gold Coin Offer
7. `reac` → Reactivation Offer
8. `dd` → Daily Deal
9. `1st`…`6th` without `po` → Conv Nth offer
10. `conv` or `boost` → Conversion Boost
11. `ftp0` without `1st`…`6th` → Other Conversion Offer
12. `dc` or month token (`jan`…`dec` / `fab`) without `conv` → Daily Campaign
13. `sun_`…`sat_` → Daily Deal
14. `otp` → OTP Offer
15. `1st`…`6th` without `ftp0` → po Nth
16. else → Other

Full enterprise extracts (not inlined here to avoid duplicating large SQL):

- FTP / reg / Seniority / player-day agg →
  [`Daily_Agg_Per_Player_Query_v1.sql`](elite_reference/Daily_Agg_Per_Player_Query_v1.sql)
- Rewards / purchase grain →
  [`Rewards_Tableau_Extract_28-5-26_v1.sql`](elite_reference/Rewards_Tableau_Extract_28-5-26_v1.sql)

## Validation

- KPI and succeeded non-refunded payment revenue must reconcile within an
  explained tolerance.
- KPI Purchased-player count must reconcile to distinct payment AIDs.
- Missing date or partition is an error.
- Treat an unexplained change of 30% or more as a warning and 50% or more as an
  error.
- Confirm timezone, report date, account-day grain, book filter, and Agent source.

## Current workflows

`Elite.MD` does not own operational schedules or output layouts. Skills and
initiative docs should cite these **Contents** headings by exact name — do not
invent alternate section titles.

- Daily and weekend report: [`daily_summary/DAILY_SUMMARY.md`](daily_summary/DAILY_SUMMARY.md)
- Daily Skill: [`.cursor/skills/daily-elite-summary/SKILL.md`](.cursor/skills/daily-elite-summary/SKILL.md)
- Purchase lookup: [`purchase_lookup/PURCHASE_LOOKUP.md`](purchase_lookup/PURCHASE_LOOKUP.md)
- WoW drop analysis: [`.cursor/skills/wow-drop-reason-analysis/SKILL.md`](.cursor/skills/wow-drop-reason-analysis/SKILL.md)
- Feedback CRO: [`feedback_cro/FEEDBACK_CRO_CANVAS.md`](feedback_cro/FEEDBACK_CRO_CANVAS.md)

The active morning router is `daily_summary/generate_morning_elite.py`, scheduled
Sun–Thu at 10:00 AM Israel time. The shared implementation lives in
`daily_summary/generate_daily_elite_summary.py`; it is a runtime dependency, not
the current report entry point.

## Reference sources

- [`elite_reference/defination_v4.docx`](elite_reference/defination_v4.docx):
  business glossary, rewards domain, and value-segment definitions (canonical
  source for those sections).
- [`elite_reference/Daily_Agg_Per_Player_Query_v1.sql`](elite_reference/Daily_Agg_Per_Player_Query_v1.sql):
  enterprise player-day SQL. Its internal `VIP` labels and 20-day churn are not
  canonical Elite reporting terminology.
- [`elite_reference/Rewards_Tableau_Extract_28-5-26_v1.sql`](elite_reference/Rewards_Tableau_Extract_28-5-26_v1.sql):
  enterprise rewards extract. Offer-type **matching order** is defined in
  Rewards and promotions above (from defination v4), not fully duplicated in
  this SQL file.
- [`AGENTS.md`](AGENTS.md): repository structure and project-wide operating rules.

Historical validation snapshots were removed from this mandatory reference.
Use dated generated reports and git history when historical evidence is needed.
