# Big Winners · Daily Triggers (Counting And Display)

Reference for `@elite-am-brief` and future chats. **Do not read export JSON** —
use `verify_brief.py` and this doc.

## Window And SQL

| Setting | Value |
|---------|--------|
| Section threshold | ≥ **$20K** player win (`BIG_WINNER_SECTION_MIN` in `config.py`) |
| Lookback | **`TRIGGER_LOOKBACK_DAYS` = 3** (inclusive of `report_date`) |
| Query | `queries.big_winners_sql` |
| Grain | **One row per AID** — the **biggest** qualifying win day in the window |
| **Created** column | That win day (not always `report_date`) |

GGR is house-side (`profit − loss`). A player win is a **negative** GGR day;
the section uses `SUM(profit − loss) ≤ −BIG_WINNER_SECTION_MIN`.

Pending RD uses a separate **$5K** flag on **report day only**
(`BIG_WINNER_MIN_PLAYER_WIN`) — do not confuse with this section.

## Non-Elite Rows (By Design)

Big Winners is the **only** section that includes **non-Elite** accounts. Those
rows have `isElite=false` and appear in **every** scored AM's payload list
(`focus_for_agent` → `filt_bw`: non-Elite OR own Elite book).

Sidebar label: **Big Winners · ≥$20K · Last 3 Days**.

## Two Audiences — Two Counts

### Per-AM Morning Brief tile

Uses `agents[].focus.bigWinners` = `len(that AM's bigWinners list)`.

Includes shared non-Elite rows, so an AM may see **1** while another sees **2**
on the same date — that is correct for “what this AM should notice.”

### Manager Dashboard · Daily Triggers tile

**Do not sum** `focus.bigWinners` across AMs. The same non-Elite player is
counted once per AM tab (e.g. five AMs → **5×** one player).

**Locked 2026-09-27:** manager roll-up uses **unique AIDs** across all
`agents[].bigWinners` (`web/src/selectors.ts` → `uniqueBigWinnersCount()` in
`views/dashboard.ts`).

## Big Winners View (Table)

| File | Rows shown |
|------|------------|
| **Manager** (`elite_am_brief.html`) | **Deduped book-wide** list — every distinct player in the 3-day window (`bigWinnersRows()`) |
| **Per-AM** (`elite_am_brief_<slug>.html`) | That file's AM list only (`rowsFor("bigWinners")`) |

The tile count and the table must match for the same file/audience after the
2026-09-27 fix.

## Worked Example (2026-09-26)

Three **unique** players in the window:

| AID | Name | Elite / AM | Win day |
|-----|------|------------|---------|
| 413998447 | Sally Hines | Non-Elite (every tab) | 2026-09-24 |
| 183747038 | Alice Kolar | Gabriel | 2026-09-26 |
| 38400050 | Daniel Smith | Lee | 2026-09-26 |

Per-AM `focus.bigWinners`: Coral 1, Gabriel 2, Lee 2, Rachel 1, Alon 1 → **sum 7**.

Manager tile (after fix): **3**. Section lists **3** rows; **Created** shows
the 9/24 win still in window.

## Looker AID Links

Account Portal (dashboard **5207**) opens with a **30-day** timeframe param on every
AID click (`elite_lib.format.looker_account_portal_url`, `web/src/looker.ts`,
`cells.ts::aidHtml`). Override via `LOOKER_ACCOUNT_PORTAL_TIMEFRAME` or full
`LOOKER_ACCOUNT_PORTAL_URL` if the filter label on 5207 differs.

## Code Map

| Piece | Location |
|-------|----------|
| Lookback constant | `config.TRIGGER_LOOKBACK_DAYS` |
| SQL | `queries.big_winners_sql` |
| Rows + per-AM focus | `payload_builders.build_big_winners_section`, `focus_for_agent` / `filt_bw` |
| Dedupe + manager rows | `web/src/selectors.ts` (`dedupeBigWinnersByAid`, `bigWinnersRows`, `uniqueBigWinnersCount`) |
| View | `web/src/views/bigWinners.ts` |
| Manager tile | `web/src/views/dashboard.ts` → `aggregateFocus()` |

## Regression Checks

After changes to Big Winners counting or manager triggers:

```bash
python -m unittest discover -s am_daily_dashboard
python am_daily_dashboard/verify_brief.py --date YYYY-MM-DD --render-check
```

On manager HTML: Daily Triggers **Big Winners** count = row count in **Big
Winners** section (unique players, not sum of AM focus).
