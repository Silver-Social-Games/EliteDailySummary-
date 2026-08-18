---
name: birthday-gift-activity
description: >-
  Compares Elite AID activity before vs after a birthday-gift checking period
  using user-supplied dates and AID lists. Use when the user asks for a birthday
  gift summary, before/after gift activity, or pastes the birthday gift request
  template.
---

# Elite Birthday Gift Activity

**Canonical workflow:** [`birthday_gift/BIRTHDAY_GIFT.md`](../../../birthday_gift/BIRTHDAY_GIFT.md)

**Fill-in template:** [`birthday_gift/REQUEST_TEMPLATE.md`](../../../birthday_gift/REQUEST_TEMPLATE.md)

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Terminology** (Hold,
Purchase) and **Revenue and Purchased players**.

## When to use

- Birthday gift before/after activity for a pasted AID list
- User fills or pastes the request template (checking periods + AIDs)
- Re-run with different dates for the same AIDs

Do **not** invent dates. Do **not** use a month-15 anchor. Do **not** pull AIDs from daily/weekend/decline reports.

## Required inputs

| Field | Required |
|-------|----------|
| Checking period — before (From / To) | Yes |
| Checking period — after (From / To) | Yes |
| AIDs | Yes (≥1) |
| Run name | Optional |

If any required field is missing, ask once for the missing pieces only.

## Template (copy into chat)

```markdown
# Birthday gift activity request

## Checking period — before
- From: YYYY-MM-DD
- To:   YYYY-MM-DD

## Checking period — after
- From: YYYY-MM-DD
- To:   YYYY-MM-DD

## AIDs
- 123456789
- 987654321

## Optional
- Run name: e.g. july_2026_cohort
- Notes:
```

## Workflow

1. Parse the filled template (or read `birthday_gift/REQUEST_TEMPLATE.md` if the user saved it).
2. Write AIDs to `birthday_gift/cohorts/{run_name}_aids.txt` (one AID per line).
3. Run the generator with explicit periods:

```bash
cd "c:\Users\Owner\Downloads\Elite"

python birthday_gift/generate_birthday_gift_activity.py \
  --aids-file birthday_gift/cohorts/{run_name}_aids.txt \
  --before-from YYYY-MM-DD --before-to YYYY-MM-DD \
  --after-from YYYY-MM-DD --after-to YYYY-MM-DD \
  --stem birthday_gift_activity_{run_name}
```

4. Build the canvas:

```bash
python birthday_gift/generate_birthday_gift_canvas.py \
  --input birthday_gift/exports/birthday_gift_activity_{run_name}.csv
```

5. Open the canvas beside chat.
6. In chat, report avg % changes for the four metrics and list any zero-activity AIDs.

**June replay shortcut** (saved AIDs + saved periods; override dates with flags if needed):

```bash
python birthday_gift/generate_birthday_gift_activity.py --cohort june_2026
```

## Metrics (fixed)

- Purchase amount ($)
- Number of purchases
- Active days
- Total SC bets
- Each: before / after / diff / % change
- Plus **LT Purchase** and **Hold**

## Data sources

| What | Source |
|------|--------|
| AIDs + periods | User template |
| Window KPIs | `jackpota_agg.daily_player_revenue_kpis` (agg by `account_id, date`) |
| LT Purchase / Hold | Lifetime sum on same KPI table |
| Agent | `dbt_utils.elite_account_tags.tag_agent_1` |
| Gift date / SC (label only) | `uam_bonus_rewards` campaign **1816** — does not set windows |

Run via Python generator (not BigQuery MCP) — KPI scans exceed MCP limits.

## Outputs

| Artifact | Path |
|----------|------|
| Detail CSV | `VIP\Elite_Cursor\Birthday Gift\birthday_gift_activity_{run_name}.csv` |
| Summary CSV | `VIP\Elite_Cursor\Birthday Gift\birthday_gift_activity_{run_name}_summary.csv` |
| HTML | `VIP\Elite_Cursor\Birthday Gift\birthday_gift_activity_{run_name}.html` |
| Canvas | `~/.cursor/projects/<workspace>/canvases/elite-birthday-gift-{run_name}.canvas.tsx` |

Player Data is sorted high → low by purchase % change. AID columns link to Looker Account Portal. No Player Data filter/sort pills.

## Terminology

Apply `.cursor/rules/elite-core.mdc`. Use **Elite**, **AID**, **Purchased players**, **Hold**.

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.
