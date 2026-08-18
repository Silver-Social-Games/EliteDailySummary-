---
name: elite-am-brief
description: Generates the Elite AM Brief morning board for Coral, Gabriel, Lee, Rachel, and Alon — per-AM canvas/HTML with Top 20 WoW gaps, pending RD, locks, birthdays, and open tickets. Use when the user asks for an AM Brief, morning AM board, Elite AM dashboard, or @elite-am-brief.
---

# Elite AM Brief

**Canonical workflow:** [`am_daily_dashboard/AM_DAILY_DASHBOARD.md`](../../../am_daily_dashboard/AM_DAILY_DASHBOARD.md)

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Terminology**, **Elite
managed book**, **Revenue and Purchased players**, **Account status and
decline reasons**. Decline reasons: `wow_drop_analysis/wow_drop_reason.py`.

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python am_daily_dashboard/generate_am_daily_dashboard.py
python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD
python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD --goals-only
```

`--goals-only` runs the single Goals query, prints the Goal / MTD / Pace / Status
audit plus that run's month-shape divisors, and writes nothing (~6s vs ~110s).
Use it when reconciling Goals numbers against an external sheet.

**Before reconciling by hand, use the reference file.** Paste the AM's own figures
into `am_daily_dashboard/data/elite_goals_reference.tsv` (same columns as
`elite_goals.tsv` plus `day`, which must equal the report date) and the audit adds
`Yours` and `Gap` columns per KPI. Blank cells do not diff; a missing file is not
an error. Ask the user for their table once and paste it — do not run several
rounds of reading numbers back and forth, which is how a 32-account roster leak
survived two days in Aug 2026.

Default report date = **yesterday**. Do **not** publish AM Brief to GitHub
Pages. Open the HTML from
`VIP\Elite_Cursor\AM Brief` (also written under `am_daily_dashboard/exports/`).

Standalone HTML refresh from existing JSON:

```bash
python am_daily_dashboard/canvas_to_html.py am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json
```

**In Cursor:** `@elite-am-brief` or "run AM Brief" / "morning AM board".

## Output

| Artifact | Path |
|----------|------|
| Canvas | `canvases/elite-am-brief-YYYY-MM-DD.canvas.tsx` (+ per-AM canvases) |
| HTML (manager) | `VIP\Elite_Cursor\AM Brief\YYYY-MM-DD_elite_am_brief.html` |
| HTML (per-AM) | `…_elite_am_brief_{coral\|gabriel\|lee\|rachel}.html` — isolated; no other AM data |
| JSON | matching `.json` beside each HTML |

After running, open the dated canvas beside chat and/or the HTML export.

## Locked product decisions

- Title **Elite AM Brief**; subtitle date only (`{Weekday} {DD Mon YYYY}`)
- **Elite Goals** — Coral / Gabriel / Lee / Rachel only, Alon omitted. Targets from
  `am_daily_dashboard/data/elite_goals.tsv`, year/month by `report_date`. MTD runs
  through `report_date` **inclusive**. Reconciled against the AMs' own table for
  Aug 1–17 2026 — full detail and every rejected alternative in
  `AM_DAILY_DASHBOARD.md`; the table below is the settled state.

  | KPI | Weight | Definition | Pace |
  |---|---|---|---|
  | Daily Avg Purchase | 15% | MTD purchased ÷ elapsed days | = actual |
  | Daily Avg Net Purchase | 15% | by-requested-redeem, see below | = actual |
  | Monthly Purchasers | 15% | distinct AIDs with a purchase in month | month-shape divisor |
  | ARPPU | 15% | derived from paced components | never paced directly |
  | Reactivation | 8% | purchase after a **≥20-day** gap, once per AID in month | `(MTD/d)*D` linear |
  | Upgrade to Elite | 5% | **unreconciled — do not trust** | month-shape divisor |
  | % Active from portfolio | 7% | last purchase **within 30 days** ÷ whole tagged book | not paced, point-in-time |

  Weights total **80%**; the manager's 20% is out of scope, so the weighted score is
  a share of included weight, not a corporate 100%. Achievement caps at 100% of goal
  (`goals_q2`-compatible). **Status compares Pace to goal, never MTD.**

  **Pace, and why two KPIs are not linear.** Monthly Purchasers and Upgrades
  *saturate* — a book can only ever run out of new people to convert — so they are
  paced as `MTD ÷ month-shape divisor`, the share of a month already reached by this
  relative day, averaged over the two prior complete months, book-wide. A linear run
  rate put Coral on pace for **914 purchasers out of a 621-player book**. ARPPU and
  % Active are rebuilt from paced components instead of paced themselves (MTD ARPPU
  is only ~55% of month-end and falsely reads Behind). If the shape is missing or
  out of band, no Pace is shown and Status falls back to MTD vs goal.

  **Net Purchase = the by-requested-redeem variant** (user-confirmed 2026-08-18 as
  the valid one): purchased − (requested redeem − cancelled) − chargeback − refunds,
  implemented as `purchased − redeemed_amt_confirmed_locked_pre − chargeback −
  refunds`. Never rebuild it from withdraw-request `status`, which is current-state
  and rewrites history; the precomputed daily column is snapshot-stable. The
  paid-redeem variant rides along as `mtdNetPurchasePaidRedeem` for reconciliation
  only.

  **A locked player still counts toward every KPI** while he is tagged and purchased
  in the calendar month (user rule 2026-08-18). **No Goals numerator filters on
  `uam_accounts.locked` — never add one**, and `% Active`'s denominator is the whole
  tagged book, locked included. `portfolioLocked` is reported but never subtracted.
  Two denominators already tried and rejected: unlocked-only (Coral 594), and an
  invented "eligible" subset that inflated % Active by 4–5 points.

  **Reactivation and % Active must match the AMs' Tableau report** — that is what
  the team is measured on. Source of truth
  `elite_reference/Daily_Agg_Per_Player_Query_v1.sql`; read it before changing
  either definition. Purchases come from `payment_payment_orders` WHERE `success`,
  not the KPI view. The 20-day gap is that query's `params.churn_period_days` — its
  inline comments saying 10 are **stale, trust the param**. Both windows live in
  `config.py` as `GOALS_REACTIVATION_GAP_DAYS` / `GOALS_ACTIVE_LOOKBACK_DAYS`;
  verified for Coral Aug 2026 (55 reactivations, 85.5% active). Show **one** number
  per KPI — the user rejected a dual MTD/trailing display. Note the two windows
  differ on purpose: Reactivation counts crossings inside the month, while % Active
  is a rolling point-in-time rate.

  **The book is pinned to the report date** via `dashboard_elite_ctes(as_of=...)`,
  because tags re-snapshot daily and books move (Rachel 557 → 589 tagged in two
  days), so an unpinned query scores one date's activity against a later roster and
  re-runs drift. Pass `as_of` for anything scored; leave it off for live sections
  (Locks, Pending RD) where the current roster is what the AM must act on.
  **`as_of` pins two things and both are required:** the tag snapshot *and*
  `dbt_aninditac.elite.agent_start_managed_date`. Pinning only the tag left the
  `COALESCE(tag, e.agent_name)` fallback reading current state, which pulled 32
  accounts into Rachel on 2026-08-17 and inflated her Daily Avg Net Purchase 11%
  while every AM who gained nobody matched to the dollar. With both filters all four
  reproduce their own table exactly (Coral $24,122 · Gabriel $23,350 · Lee $24,929 ·
  Rachel $24,177). Keep NULL managed dates. Do not swap the managed date for a
  "first tagged" proxy — all 34 disputed accounts were first tagged the same day,
  and only the managed date keeps Gabriel's 2 while dropping Rachel's 28.

  **Before blaming an AM-specific bug, check the book.** Gabriel is the only AM
  whose tag has two spellings (`gabriel` / `gabriel_e`) collapsed into one, so he is
  where duplicate rows would inflate SUM metrics — verified clean 2026-08-18 (only
  `gabriel_e`, zero multi-row accounts), and his MTD purchase and purchaser count
  reconcile to the dollar against raw `payment_payment_orders`. His low ARPPU is
  real: ~$74 average order vs Coral's $89 on comparable volume.

  Per-AM HTML/JSON are **file-level isolated** — no Overview, no AM switcher, no
  other AM's data, and `goalsAmOrder` is narrowed so the file does not even carry
  who else is measured.
- **The 96% % Active target is a deliberate stretch goal — do not flag it as a data
  bug.** July actuals were 86.7–89.7%, and a 546-purchaser + 96%-active pair is only
  self-consistent for a ~569-player book, so a bigger book (Gabriel: 646) reads
  lower by design.
- **`Upgrade to Elite` is unreconciled — treat its Status as untrustworthy.** The
  board reads the first in-month Elite tag snapshot (`dbt_utils.elite_account_tags`,
  history from 2026-04-08) and gives 53/46/48/26 for Aug 1–17 2026 against the AM's
  8/6/7/9 — an order of magnitude apart, so it is a different set of accounts.
  Already ruled out (2026-08-18): `agent_start_managed_date` in month, a "never
  under another AM" filter, and first-purchase / account-created in month. Closest
  fit is managed date in month plus account created within 60 days before month
  start (7/6/8/4) — **do not adopt it**, it is tuned to the data. Waiting on the
  user for the Tableau field behind their column.
- Top purchasers: **Purchases (#)**, Top Offer, **Price**, **Usual → Ceiling (30D)**
  (no Qty / Offer $). Price = that offer's cost as the player paid it, cents kept
  (`$899.99`, never rounded to `$900`), marked `avg` when the same offer sold at more
  than one amount. Usual = most-bought 30D price point (ties → higher); Ceiling =
  highest price paid **at least twice** in 30D, so a one-off does not set an upsell
  target. A missing `→ ceiling` means no proven headroom, not missing data.
  **A 7D/30D average was asked for, built, tested and rejected — do not re-add it.**
  These players buy at 15–25 price points a month, so a mean names no sellable
  package (one averaged $33/order while habitually buying $19.99 and repeatedly
  $299.99). Momentum and cadence were designed and deliberately dropped to keep the
  section narrow. `build_package_fit` formats the cell once for all three
  implementations — change it there, not in each renderer
- **Goals score = 80 KPI points + the manager's 20, total 100.** Appreciation is
  hand-entered per AM per month in `data/elite_manager_appreciation.tsv` (committed
  headers-only, so nobody starts scored). A missing file is not an error, points
  clamp to 0–20, and **a blank points cell means not scored, not zero.** An unscored
  AM reads `NN.N / 80` and `Manager Pending` — **never `/100`**, because that would
  spend the manager's 20 points on the AM's behalf (same honesty rule as the Docs
  column). The 80 and the 20 render as **two separate tracks** with a gap and
  rounded ends — do not merge them into one meter. Violet is the manager hue,
  deliberately outside the status palette; canvas uses `theme.category.purple` and
  `theme.stroke.primary` (`theme.border.default` does not exist in the SDK). The
  manager leaderboard ranks on `totalPctOfMax`, not raw points, since a scored AM is
  out of 100 and an unscored one out of 80. Streamlit does not render Goals at all
- **Archive calendar** — dateless `elite_am_brief.html` / `elite_am_brief_<slug>.html`
  are rewritten every run so a bookmark survives; dated files are the archive. The
  topbar month calendar only enables days whose file exists, because
  `archive_entries()` **lists the export folder** rather than computing dates (the
  board skips Fri/Sat and misses runs, so arithmetic would produce dead links). The
  list is built **per audience** — an AM must never be offered a date their own file
  does not exist for. History starts fresh from when the tool ships; no backfill
- **Pending RD** ≥ threshold created in last N days — `config.py` (`PENDING_RD_MIN_AMOUNT` = $5k, `PENDING_RD_LOOKBACK_DAYS` = 3). Also carries **Won Yesterday** / **Docs** / LTP / Hold / 7D Purchase (Batch 8 item 2). Won Yesterday flips the house-side GGR sign — a player win is a **negative** GGR day — and shows `—` on a losing day, never a negative win; at `config.BIG_WINNER_MIN_PLAYER_WIN` ($5k) it adds a `· Big Winner` label, which **outranks** the ageing highlight for row tone. **Docs is blank when nothing is flagged and must stay that way:** the source proves only "no open ticket names a missing document", never that documents are verified complete, so a green "all docs OK" would be a claim the data cannot support to a player awaiting a withdrawal. Neither field costs a query — GGR joins inside `locked_rd_over_5k_sql`, and docs/LTP/Hold/7D reuse the `enrich_aids_sql` batch already fetched for Open Tickets
- **Locks** = still locked **and** [`locked_at` within `config.LOCKS_WINDOW_DAYS` of report_date (1 = today only; any lock reason) **or** Take a break whose unlock date is within `config.LOCKS_REVIEW_WINDOW_DAYS` days or already passed, regardless of lock age] — the second path exists so an overdue break is never missed just because it's no longer "new"; rows sort by soonest unlock, today/overdue render danger
- **Birthdays** window — `config.BIRTHDAYS_LOOKBACK_DAYS` = 3
- **AID always links to Looker; Open Tickets' TIDs always link to Zendesk** — every section, no exceptions
- **Filters only where needed** — search box stays on Top 10 Purchasers, Top 20 · WoW Purchase Gaps, and Open Tickets; removed from Pending RD, First-Time Locked RD, Birthdays, Locked/Take A Break (`showSearch` option, default true). Sort controls are a separate `sortOptions`/`sortFn` mechanism on the same `SearchableTable`/`searchableSection` — Open Tickets (LTP ↓ default) and Pending RD (Amount ↓ default) have one; Locked/Take A Break sorts by soonest unlock automatically with **no** visible control (kept out of the filter bar on purpose)
- **Compact tables** — Morning Checklist and Top 10 Purchasers size to their content (`tableStyle`/`style={ width: "max-content" }` on canvas, `.compact-frame` class on HTML) instead of stretching the full panel width like other sections; opt-in per call site
- **Churned (7d), Active Decliners and Milestone Alerts were removed 2026-08-18 — do not re-add them without asking.** They were built despite the user asking to exclude them, cost a BigQuery query each, and this doc previously carried a note that entrenched them. When an instruction and existing code disagree, ask; do not document the code as settled. Churn and Active decliner still live in `daily_summary`, and `elite-core.mdc` still owns the definitions. The first removal pass missed the *presentation* layer — nav entries, checklist and dashboard tiles survived in the HTML, and the canvas checklist read `focus.churned`, a field the payload and the `Focus` type had already dropped. **Removing a section means grepping all three implementations** (`canvas_parts/`, `handoffs/elite_am_brief_web.html`, `daily_summary/streamlit_app/am_brief_app.py`), not just the query layer
- **Top 20** via `fetch_top_same_day_by_agent` (same selection/classify as Elite Daily Decline; up to 20 per AM)
- HTML via `canvas_to_html` interactive shell (Overview + AM tabs for manager; per-AM files stripped) — **not** a static table dump
- **Not** on GitHub Pages — Daily/Weekend publish to `docs/`; AM Brief stays local
- Canvas render logic lives in `am_brief_canvas.py` (top-level App + JSON wiring) + `canvas_parts/{cells,tables,sections}.py` (`sections.py` = `AgentPanel`, the actual per-AM-tab section composition — edit here for one section's columns/filter/thresholds). The standalone HTML (`handoffs/elite_am_brief_web.html`) is a **separate, independent** implementation of the same UI — mirror any section/filter change there too until unified (see Roadmap in `AM_DAILY_DASHBOARD.md`)
- **Ticket drafts are review-only, never auto-sent** — Top 20 WoW Gaps (`wow_drop_analysis/ticket_draft.py`) plus First-Time Locked RD and Birthdays (new — `am_daily_dashboard/am_brief_ticket_drafts.py`). All three refuse to offer a draft for a locked or self-excluded account (elite-core rule); the Ticket column shows the lock label instead. WoW Gaps drafts also append the row's literal Reason + Recommendation as an agent-only internal note in the message body

## Sections (see canonical doc)

Overview + per-AM tabs: Empowering intro, **Elite Goals** (4 AMs), Elite & Jackpota + AM share, Morning Checklist, Top 10 Purchasers, Top 20 · WoW Purchase Gaps, Pending Redemptions, First-Time Locked RD, Birthdays · Last 3 Days, Open Tickets, Locked And Take A Break.

## Open work

Backlog with full intent and open questions: *Roadmap / Backlog* in
`AM_DAILY_DASHBOARD.md`. Short version:

- **Batch 10 (score out of 100 + archive calendar) is code-complete but NEVER RUN.**
  Written 2026-08-18; 38 unit tests pass and the HTML JS syntax-checks, but the
  generator was not executed after the edits. **Do this first:**
  `python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-17`, then
  check the Goals card reads `NN.N / 80` with a dashed empty manager track, the
  topbar calendar navigates to another day, and the dateless
  `elite_am_brief_<slug>.html` files reach Elite_Cursor. Details:
  *Score out of 100* and *Archive calendar* in `AM_DAILY_DASHBOARD.md`.
- **Batch 8, worked one at a time. Items 1 (Top Purchasers price ladder) and 2
  (Pending RD big winner + docs) shipped 2026-08-18** — see the bullets above.
  Remaining: a new Big Winners ≥ $20K section; last win above 1K SC; Open Tickets
  weighted prioritisation (weights settled, topic set still to define). Two scope
  questions already settled:
  **Big Winners includes non-Elite players in every AM's own view** (the only section
  that reaches outside the Elite book — label those rows, and do not copy the wider
  filter elsewhere); **ticket weights normalise to 100%** (LT hold 25, LT NGR 20, LT
  purchase 20, 30D purchase 25 → 27.8/22.2/22.2/27.8).
- **Then — Batch 9:** trending games board, dormant favourite game flag (flag only
  when the player had a **net loss** on that game).
- **Batch 7 UI/UX overhaul — done, close it, do not build it.** All four asks exist
  in the standalone HTML: left sidebar nav, manager-only gated dashboard, inline SVG
  icons, and table pagination (`paginate()`, wired generically through `tableCard` /
  `searchableSection` plus Top 20). Earlier notes wrongly said pagination was
  outstanding. The canvas and Streamlit implementations
  have no sidebar, so they have drifted from the HTML.
- **Blocked:** Zendesk auto-create — agreed as **internal notes only, AM Brief
  only**, waiting on API credentials. The "one month since AM assignment" rule needs
  its definition settled; `agent_start_managed_date` is the column it should use.
- **GGR sign:** a player big win is a **negative** GGR day (`Elite.MD`: `profit −
  loss`). Both big-winner asks invert if this is read backwards.

## Terminology

Apply `.cursor/rules/elite-core.mdc` and `.cursor/rules/bigquery-analytics.mdc`.
Use **Elite**, **AID**, **Purchased players**. TID = Zendesk ticket ID.

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.
