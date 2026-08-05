# 60 Days No Purchase Last Push

Quarterly export of **managed Elite** players with **no purchase in the past 60 days**. Locked/closed accounts are excluded.

---

## Schedule

| Item | Value |
|------|-------|
| **Name** | 60 Days No Purchase Last Push |
| **Frequency** | Every 3 months, **1st of the month** at **09:00** |
| **Run dates** | 1 Jan · 1 Apr · 1 Jul · 1 Oct |
| **Next run** | **2026-10-01** (after task registration) |

Register once (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File last_push_60d\register_60_days_no_purchase_last_push_task.ps1
```

---

## Manual run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python last_push_60d/generate_60_days_no_purchase_last_push.py
python last_push_60d/generate_60_days_no_purchase_last_push.py --date YYYY-MM-DD
```

---

## Where files are saved

**Canonical output folder:**

```
last_push_60d/exports/
```

**Filename pattern:**

```
YYYY-MM-DD_60_days_no_purchase_last_push.csv
```

Example: `last_push_60d/exports/2026-10-01_60_days_no_purchase_last_push.csv`

Full path: `c:\Users\Owner\Downloads\Elite\last_push_60d\exports\`

Each scheduled run creates a **new dated file** (history is kept; files are not overwritten across quarters).

---

## Export columns

| Column | Source |
|--------|--------|
| AID | `account_id` |
| Account Manager | `tag_agent_1` → friendly name |
| First Name / Last Name / Name | `uam_persons` + `uam_accounts` |
| Email | `uam_accounts.email` |
| Last Purchase Date | Last KPI day with `purchased > 0` |
| Last Purchase Amount | `purchased` on that day (account-day agg) |
| LT Purchase | Lifetime `SUM(purchased)` |
| Net Purchase | Lifetime `SUM(purchased - redeemed - chargeback - refunds)` |

---

## Cohort rules

- **Elite book:** `dbt_aninditac.elite` + assigned `tag_agent_1` (`dbt_utils.elite_account_tags`)
- **60-day window:** report date minus 59 days through report date (inclusive)
- **Excluded:** `uam_accounts.locked = TRUE` (any lock reason)

See [`Elite.MD`](../Elite.MD) **Terminology**, **Elite managed book**, and
**Revenue and Purchased players** for KPI grain and book filter.
