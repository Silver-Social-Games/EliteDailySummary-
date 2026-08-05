# Declining Players — Friday–Saturday Promo

Bonus on **3rd** and **5th** purchase only, using Elite trimmed-avg **target offer** buckets. Bonuses rounded **UP** to nearest **$5**. Use **purchase** (not buy) in reach-outs.

**Definitions:** [`Elite.MD`](../Elite.MD) — **Terminology** and **Rewards and
promotions**.

This is a supplied CSV cohort, not a regenerated canonical Elite-book cohort.
Use the input roster as the audience unless dashboard reconciliation is
explicitly requested.

| Event | Rate |
|-------|------|
| 3rd purchase | **10%** |
| 5th purchase | **15%** |

## Generate

```bash
python declining_fri_sat_promo/generate_declining_fri_sat_promo.py
```

## Inputs

| File | Role |
|------|------|
| `c:\Users\Owner\Downloads\Declining Players (15).csv` | Promo audience |
| `c:\Users\Owner\Downloads\elite_vip_trimmed_avg_target_list_TO_ALon_16.7.xlsx` | Target offer buckets |

## Outputs

| Path | Contents |
|------|----------|
| `exports/declining_players_fri_sat_promo_buckets.xlsx` | Players, bucket summary, economics, rules, email copy, unmatched |
| `exports/declining_players_fri_sat_promo_buckets_10_15.xlsx` | Same workbook (use if the main file is open/locked) |
| `exports/team_email_copy.txt` | Paste-ready team email |
| `c:\Users\Owner\Downloads\declining_players_fri_sat_promo_buckets.xlsx` | Same workbook copy in Downloads |

## Bonus by bucket

| Purchase at | 3rd (10%) | 5th (15%) | Max total |
|-------------|-----------|-----------|-----------|
| $34.99 | $5 | $10 | $15 |
| $69.99 | $10 | $15 | $25 |
| $119.99 | $15 | $20 | $35 |
| $199.99 | $20 | $30 | $50 |
| $299.99 | $30 | $45 | $75 |

Purchases 1, 2, and 4: no bonus.
