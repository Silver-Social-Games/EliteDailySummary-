# Looker Account Portal (Dashboard 5207)

AID links on the AM Brief (and other Elite tools) open:

`https://lookerpatrianna.cloud.looker.com/dashboards/5207`

## Why links can still show Last 7 Days

Looker **ignores** URL filter tokens that do not **exactly** match the dashboard
filter **name** and **value** as they appear in the browser when you set
**Last 30 Days** manually. Wrong token → dashboard keeps its default (often
**Last 7 Days**).

The board **does** append a timeframe query param on every AID click via
`web/src/looker.ts` → `cells.ts::aidHtml()` (all tabs). The open issue is the
**correct token**, not missing wiring.

## Fix (one-time calibration)

1. Open dashboard **5207** in Looker (no AID).
2. Set the date/time filter to **Last 30 Days** (confirm the UI shows 30 days).
3. Copy the **full URL** from the address bar.
4. Note every `Filter+Name=value` pair (especially the timeframe — may **not** be
   named `Timeframe`).
5. Update **both**:
   - `elite_lib/format.py` → `DEFAULT_LOOKER_ACCOUNT_PORTAL_TIMEFRAME` (value only)
     or full `DEFAULT_LOOKER_ACCOUNT_PORTAL_URL` / env `LOOKER_ACCOUNT_PORTAL_URL`
   - `am_daily_dashboard/web/src/looker.ts` → `LOOKER_ACCOUNT_PORTAL_TIMEFRAME`
     (keep in sync with Python)
6. Rebuild: `node am_daily_dashboard/web/build.mjs`
7. Refresh HTML: `python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --html-only --cursor-audience manager`
8. Test: `python am_daily_dashboard/scripts/capture_looker_portal_url.py <AID>`

**Env overrides (no code edit):**

- `LOOKER_ACCOUNT_PORTAL_TIMEFRAME` — value segment only (e.g. `last+30+days`)
- `LOOKER_ACCOUNT_PORTAL_URL` — full template with `{aid}` / `{account_id}`

## Code map

| Layer | File |
|-------|------|
| Python (payload `aidUrl`, Slack, daily summary, …) | `elite_lib/format.py` |
| HTML (all AID clicks) | `web/src/looker.ts`, `web/src/cells.ts` |
| Tests | `elite_lib/test_format.py`, `test_payload_builders.py` |

## Calibrated default (2026-09-27)

Code and tests use this pair until a UI check replaces it in
`data/looker_account_portal_query.tsv`:

| Piece | Value |
|-------|--------|
| Filter **name** (URL key) | `Timeframe` |
| Filter **value** (Looker relative expression) | `last 30 days` |
| URL segment (spaces → `+`) | `Timeframe=last+30+days` |

Example (AID `123456789`):

`https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+=123456789&Timeframe=last+30+days`

Generate a link anytime:

```bash
python am_daily_dashboard/scripts/capture_looker_portal_url.py <AID>
```

**UI confirmation (still required):** open that URL signed into Looker. The date
control must read **Last 30 Days**, not **Last 7 Days**. If it stays on 7 days,
the filter name or value token is wrong — repeat **Fix** steps 1–5 with the
address bar after you set 30 days manually, then update the TSV row and both code
paths.

Looker relative-date URLs use lowercase `last+30+days` (plus signs for spaces),
not title case `Last+30+Days`.
