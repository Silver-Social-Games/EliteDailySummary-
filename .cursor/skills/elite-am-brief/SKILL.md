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
- Top purchasers: **Purchases (#)** + Top Offer (no Qty / Offer $)
- **Pending RD** ≥ threshold created in last N days — `config.py` (`PENDING_RD_MIN_AMOUNT` = $5k, `PENDING_RD_LOOKBACK_DAYS` = 3)
- **Locks** = still locked **and** [`locked_at` within `config.LOCKS_WINDOW_DAYS` of report_date (1 = today only; any lock reason) **or** Take a break whose unlock date is within `config.LOCKS_REVIEW_WINDOW_DAYS` days or already passed, regardless of lock age] — the second path exists so an overdue break is never missed just because it's no longer "new"; rows sort by soonest unlock, today/overdue render danger
- **Birthdays** window — `config.BIRTHDAYS_LOOKBACK_DAYS` = 3
- **AID always links to Looker; Open Tickets' TIDs always link to Zendesk** — every section, no exceptions
- **Filters only where needed** — search box stays on Top 10 Purchasers, Top 20 · WoW Purchase Gaps, and Open Tickets; removed from Pending RD, First-Time Locked RD, Birthdays, Locked/Take A Break (`showSearch` option, default true). Sort controls are a separate `sortOptions`/`sortFn` mechanism on the same `SearchableTable`/`searchableSection` — Open Tickets (LTP ↓ default) and Pending RD (Amount ↓ default) have one; Locked/Take A Break sorts by soonest unlock automatically with **no** visible control (kept out of the filter bar on purpose)
- **Compact tables** — Morning Checklist and Top 10 Purchasers size to their content (`tableStyle`/`style={ width: "max-content" }` on canvas, `.compact-frame` class on HTML) instead of stretching the full panel width like other sections; opt-in per call site
- **Churned (7d), Active Decliners and Milestone Alerts were removed 2026-08-18 — do not re-add them without asking.** They were built despite the user asking to exclude them, cost a BigQuery query each, and this doc previously carried a note that entrenched them. When an instruction and existing code disagree, ask; do not document the code as settled. Churn and Active decliner still live in `daily_summary`, and `elite-core.mdc` still owns the definitions
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

- **Next — Batch 8, five team-feedback asks**, worked one at a time: Top Purchasers
  avg purchase 7D/30D + price; Pending RD big winner + missing-docs status; a new
  Big Winners ≥ $20K section; last win above 1K SC; Open Tickets weighted
  prioritisation. **Three need a decision from the user before building** — what
  "price" means, whether Big Winners really includes non-Elite, and what the missing
  30% of the ticket weights is (given weights sum to 70%).
- **Then — Batch 9:** trending games board, dormant favourite game flag (flag only
  when the player had a **net loss** on that game).
- **Requested, not started:** Batch 7 UI/UX overhaul — left sidebar nav,
  manager-only dashboard, real design pass with **inline** SVG icons (files open
  from OneDrive, so no CDN), table pagination. Re-check whether pagination is still
  worth it now that the three large sections are gone.
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
