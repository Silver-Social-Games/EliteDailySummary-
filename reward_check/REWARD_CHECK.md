# Elite Reward Checker

Local Streamlit tool for CRM and Elite to verify whether one player received:

- Free Spins
- SC/GC included with a purchase
- Platform Tournament prizes

**Definitions:** [`Elite.MD`](../Elite.MD) — **Terminology** and **Rewards and
promotions**.

## Run locally

```powershell
cd "c:\Users\Owner\Downloads\Elite"
python -m pip install -r requirements.txt
streamlit run reward_check/app.py
```

Open `http://localhost:8501`, then search by exact **AID** or email.

CLI example:

```powershell
python reward_check/generate_reward_check.py `
  --search 253808059 `
  --type free_spins `
  --offer-code conv_20kg_10s_9_99 `
  --expected-fs 125 `
  --from 2026-07-13 `
  --to 2026-07-14 `
  --zendesk-tid 608022
```

TID means **Zendesk ticket ID**. It is never treated as an Order ID or purchase transaction ID.

## Minimal data paths

| Check | Primary tables | Optional fallback |
|---|---|---|
| Identity/status | `transactional_data.uam_accounts` | `dbt_utils.elite_account_tags` for Agent |
| Purchase SC/GC | `payment_payment_orders` + `payment_offer_templates` | None required |
| Free Spins | `uam_account_free_spins` + `uam_free_spin_campaigns` | `fact_rewards`; `fact_gameplay_daily` |
| Tournament prize | `uam_bonus_rewards` + `core_products` | Admin system for rank/name |

All searches first resolve to one AID. Email is matched exactly and masked in the UI.

## Decision rules

### Free Spins

The wallet tables are the issuance source of truth:

- **Received and unused:** matching grant exists with `left_spins > 0`
- **Received and used:** matching grant has `used` populated or is finished with zero remaining
- **Received but expired:** matching grant exists but expired before use
- **Partial:** matching grant count is lower than promised
- **Missing:** qualifying purchase succeeded, but no matching wallet or rewards-ledger grant exists
- **Inconclusive:** the purchase/offer cannot be identified

`fact_rewards` is secondary evidence. It may not contain unused FS and its per-spin rows can inflate naive totals. The tool groups reward rows and uses `reward_count` / campaign totals rather than summing repeated `total_spins`.

### Purchase SC/GC

An order qualifies when:

```text
status = succeeded
refunded = false
```

`payment_payment_orders.sc_amount` and `gc_amount` are authoritative for the purchase credit. Bonus SC is:

```text
MAX(sc_amount - purchase amount, 0)
```

### Tournament prize

Platform Tournament payouts are accepted `uam_bonus_rewards` rows with:

```text
product_id = 8990
```

The tool compares the paid SC/GC against the expected prize.

## What the tool cannot prove

- BigQuery does not expose tournament ID, tournament name, or leaderboard position.
- `fact_gameplay_daily` is aggregated by day/game; it cannot prove one exact spin from a screenshot.
- A screenshot win is gameplay return, not necessarily a separate reward credit.
- No result should be used to recommend outreach when the account is locked or self-excluded.

## Security and deployment

The MVP runs locally. Do not publish player search data or BigQuery credentials to GitHub Pages.

For team access, deploy the Streamlit app to an authenticated backend such as Google Cloud Run and link to it from the existing report site. Keep credentials server-side and restrict access to approved company accounts.
