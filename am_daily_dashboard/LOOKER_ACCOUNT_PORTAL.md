# Looker Account Portal (Dashboard 5207)

AID links on the AM Brief (and other Elite tools) open:

`https://lookerpatrianna.cloud.looker.com/dashboards/5207`

## Why `Timeframe=` Did Not Work

Dashboard **5207** does not use a filter named `Timeframe`. Wrong token → default
**Last 7 Days** stayed in the UI.

**Calibrated 2026-09-27 (browser URL after setting 30 days):**

| Piece | Value |
|-------|--------|
| Filter **name** (URL key) | `Purchase filter date` → `Purchase+filter+date` |
| Filter **value** (UI: 30 day) | `30+day` |

Example (AID `183747038`):

`https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+=183747038&Purchase+filter+date=30+day`

Empty filters (`Internal (Yes / No)`, `Email Filter`) are optional; Account ID +
purchase date are enough.

## Fix After A Dashboard Change

1. Open dashboard **5207**, set **Purchase filter date** to **30 day**, add an AID.
2. Copy the **full URL** from the address bar.
3. Update **both**:
   - `elite_lib/format.py` → `DEFAULT_LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE` (value only)
     or full `DEFAULT_LOOKER_ACCOUNT_PORTAL_URL` / env `LOOKER_ACCOUNT_PORTAL_URL`
   - `am_daily_dashboard/web/src/looker.ts` → `LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE`
4. Rebuild: `node am_daily_dashboard/web/build.mjs`
5. Refresh HTML: `python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --html-only --cursor-audience manager`
6. Test: `python am_daily_dashboard/scripts/capture_looker_portal_url.py <AID>`

Log confirmations in `am_daily_dashboard/data/looker_account_portal_query.tsv`.

**Env overrides (no code edit):**

- `LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE` — value segment only (e.g. `30+day`)
- `LOOKER_ACCOUNT_PORTAL_URL` — full template with `{aid}` / `{account_id}`

## Code Map

| Layer | File |
|-------|------|
| Python (payload `aidUrl`, Slack, daily summary, …) | `elite_lib/format.py` |
| HTML (all AID clicks) | `web/src/looker.ts`, `web/src/cells.ts` |
| Tests | `elite_lib/test_format.py`, `test_payload_builders.py` |

