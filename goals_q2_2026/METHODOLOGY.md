# Q2 2026 Elite Goals Evaluation — Methodology

**Definitions:** [`Elite.MD`](../Elite.MD) — **Terminology** and **Revenue and
Purchased players**.

## Scoring model

| Block | Max |
|-------|-----|
| KPI goals | 80% |
| Manager evaluation | 20% (assigned per agent) |
| **Total** | **100%** |

### KPI weights (80%)

| KPI | Weight |
|-----|--------|
| Daily Avg Purchase | 20% |
| Daily Avg Net Purchase | 25% |
| Monthly Purchasers | 15% |
| # Reactivation | 8% |
| Upgrade to Elite | 5% |
| % Active from portfolio | 7% |

### Eligibility

| Agent | Counted months |
|-------|----------------|
| Coral | April + May + June |
| Lee | May + June only |
| Rachel | June only |

Ineligible months are **excluded** from scoring (not treated as misses).

### Achievement formula

For each KPI (except Upgrades):

```
Achievement% = min(100%, sum(Actual over eligible months) / sum(Goal over eligible months))
KPI points   = Achievement% × KPI weight
```

Shortfalls receive **partial credit**. Overperformance is capped at 100% of the KPI weight.
Multi-month catch-up is automatic via the eligible-window sum ratio.

**Upgrade to Elite:** forced to **100%** (full 5%) for every agent.

### Manager scores & notes

| Agent | Manager % | Note |
|-------|-----------|------|
| Coral | +15% | Improve time management; dive deeper when she doesn't understand. |
| Lee | +12% | Sometimes gives up early, doesn't go deep (VIP Event); needs to improve depth/follow-through. |
| Rachel | +10% | Improve time management; messy. Must learn to be organized; learn to receive feedback. |

### Presentation rounding

Submitted **Goals %** and **Final %** are rounded **up** (ceiling) to whole percentages.
Exact decimals are retained in audit CSVs.

### Source

`Goals w Agent V2.csv` — Actual vs Goal columns only; sheet Yes/No flags ignored.

### Outputs

- `exports/q2_2026_elite_goals_evaluation.html` — CEO HTML pack
- `exports/q2_2026_scoreboard.csv`
- `exports/q2_2026_kpi_audit.csv`
- `exports/q2_2026_monthly_detail.csv`
