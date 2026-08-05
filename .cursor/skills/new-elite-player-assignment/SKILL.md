---
name: new-elite-player-assignment
description: Splits monthly New Elite player CSV exports among Coral, Gabriel, Lee, and Rachel using exact player quotas and balanced purchase value, then creates or extends a formatted Excel workbook. Use when the user asks to organize, distribute, assign, or add new Elite players from a VIP Potential CSV.
---

# New Elite Player Assignment

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Terminology** (AID, Agent)
and **Elite managed book**. This skill assigns from a VIP Potential CSV export;
it does not rebuild the dashboard Elite book.

## Required inputs

Confirm these before generating:

1. Source CSV path.
2. Current player count for each Agent, or exact new-player quota per Agent.
3. Output workbook path.
4. Whether an existing workbook should be used as the base.

Never infer conflicting quotas. Show the quota math and confirm it when the
user has not provided exact counts.

## Quota calculation

When the goal is equal final ownership:

```text
target = (sum(current counts) + new player count) / agent count
quota[agent] = target - current count[agent]
```

Use integer quotas that add to the CSV row count. If the target is not an
integer, distribute the remainder to Agents with the largest deficits.

If the user gives exact quotas, use them. Validate that their sum equals the
number of CSV players.

## Assignment rules

1. Read the UTF-16, tab-separated CSV.
2. Treat `account_id` as **AID** in explanations, but preserve the source
   column name in the workbook unless the user asks to rename it.
3. Parse the balancing column as numeric by stripping `$`, commas, `%`, and
   whitespace.
4. Default balancing column: `Net Purchases`.
5. Sort candidates high to low by the balancing column.
6. Assign each candidate to the eligible Agent with the lowest running
   balancing total, enforcing the exact quota for every Agent.
7. Never assign an AID more than once.
8. Sort every Agent tab high to low by the balancing column.

`Net Purchases` may be used internally while hidden from every workbook tab.
Default to hiding it unless the user explicitly asks to display it.

## Generate

Run the initiative generator from the repository root:

```bash
python new_elite_players_adding/generate_assignment.py --input "PATH/TO/VIP Potential.csv" --output "PATH/TO/New_Elite_Players.xlsx" --quota Coral=62 --quota Gabriel=84 --quota Lee=66 --quota Rachel=32 --base "PATH/TO/previous_workbook.xlsx" --remove-balance-from-all-sheets
```

Omit `--base` to create a new workbook. Omit
`--remove-balance-from-all-sheets` when inherited tabs should remain
unchanged.

## Workbook format

Create one tab per Agent with suffix `New`, plus `New Additions Master`.
Use the same columns and order on every Agent tab:

```text
# | account_id | first_name | last_name | email |
Avg. LT_net_purchases_ByReq | Avg. LT_purchased |
LT Hold | Previous 30d Purchased *
```

Formatting:

- Bright Agent-specific header and tab colors.
- White bold headers, alternating row shading, frozen header row.
- Real numeric Excel values and appropriate number formats.
- Auto-fit columns.
- `Assigned To` on the master tab.

## Verification

Do not hand off until all checks pass:

- Per-Agent row counts equal the confirmed quotas.
- Total assigned rows equal the source CSV row count.
- Unique AID count equals assigned row count.
- No visible balancing column when it should be hidden.
- Report internal balancing totals per Agent in chat.
- If the output is locked, save a clearly named corrected copy and report why.

