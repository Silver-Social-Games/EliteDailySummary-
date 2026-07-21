# Birthday gift activity

Before/after Elite activity for a user-supplied AID list and checking periods.

## Inputs

Use [`REQUEST_TEMPLATE.md`](REQUEST_TEMPLATE.md):

- **Checking period — before** (From / To)
- **Checking period — after** (From / To)
- **AIDs**

No month-15 anchor. Dates are never auto-derived.

## Metrics

| Metric | Definition |
|--------|------------|
| Purchase amount ($) | Sum of account-day `purchased` in the period |
| Number of purchases | Sum of `purchased_num` |
| Active days | Days with `spins > 0` |
| Total SC bets | Sum of `profit` |
| LT Purchase | Lifetime sum of `purchased` |
| Hold | Lifetime net purchase ÷ lifetime purchased |

Per metric: before, after, diff, % change.

## Data sources

| What | Table |
|------|-------|
| KPIs | `jackpota_agg.daily_player_revenue_kpis` |
| Agent | `dbt_utils.elite_account_tags.tag_agent_1` |
| Gift label (optional) | `transactional_data.uam_bonus_rewards` campaign 1816 |

AIDs come from the template only — not from daily/weekend/decline reports.

## Commands

```bash
python birthday_gift/generate_birthday_gift_activity.py \
  --aids-file birthday_gift/cohorts/{run_name}_aids.txt \
  --before-from YYYY-MM-DD --before-to YYYY-MM-DD \
  --after-from YYYY-MM-DD --after-to YYYY-MM-DD \
  --stem birthday_gift_activity_{run_name}

python birthday_gift/generate_birthday_gift_canvas.py \
  --input birthday_gift/exports/birthday_gift_activity_{run_name}.csv
```

Skill entry point: `@birthday-gift-activity`
