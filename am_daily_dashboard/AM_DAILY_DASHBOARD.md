# Elite AM Brief

Morning board for Coral, Gabriel, Lee, Rachel, and Alon — complementary to the Elite Daily Decline Top 20.

**Definitions:** [`Elite.MD`](../Elite.MD) · **Decline reasons:** `wow_drop_analysis/wow_drop_reason.py`

---

## Start here

Read this section plus the Skill (`.cursor/skills/elite-am-brief/SKILL.md`) and you
have the current state. Everything below is detail and history.

**State as of 2026-08-18.** Eleven sections per AM tab, plus Overview for the
manager. Elite Goals is built and reconciled: Daily Avg Purchase, Daily Avg Net
Purchase and Monthly Purchasers match the AMs' own table **exactly** for all four,
% Active lands within a point, and Upgrade to Elite is **knowingly wrong** and must
not be treated as scored. Batches 1 and 3–4 are done; Batch 5 was built and then
reverted at the user's request.

Batch 8 items 1 (Top Purchasers price ladder) and 2 (Pending Redemptions big winner
+ docs) shipped 2026-08-18.

**Batch 10 (score out of 100 + archive calendar) is code-complete but NOT yet
verified end to end.** Written 2026-08-18 and left at exactly that point when the
session ran out of context. Unit tests (38) pass and the HTML JS syntax-checks, but
**the generator has not been run since these edits**. First action in a new chat:

```
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-17
```

then confirm (a) every AM's Goals card reads `NN.N / 80` with a dashed empty
manager track and the legend saying `Manager Pending`, (b) the topbar calendar
opens and a highlighted day navigates to that day's file, (c) the dateless
`elite_am_brief_<slug>.html` files exist and mirror to Elite_Cursor. See
*Score out of 100* and *Archive calendar* below for what was built and why.

**Batch 7 is done — close it, do not build it.** All four asks exist in the
standalone HTML: left sidebar nav, manager-only gated dashboard, inline SVG icons,
and table pagination (`paginate()`, wired generically through `tableCard` /
`searchableSection` plus Top 20). An earlier note here wrongly said pagination was
outstanding. The canvas and Streamlit implementations do not have the sidebar, so
they have drifted, but that is the known architecture gap, not Batch 7 work.

**Next up:** Batch 8 items 3–5, one at a time. Item 5's weights are settled but its
ticket-topic set still needs defining with the user; items 3–4 carry a presentation
question each. Then Batch 9 (trending games, dormant favourite game).

**Blocked:** Zendesk auto-create (waiting on API credentials) and the "one month
since AM assignment" rule (definition never settled).

### Do not re-litigate these

Each cost real time to settle. Reasons and rejected alternatives are documented in
the sections named.

| Settled | Short version |
|---|---|
| Book pinning | `as_of` must filter **both** the tag snapshot **and** `agent_start_managed_date`. One without the other silently mixes rosters. → *Pinning takes two filters* |
| Net Purchase | The **by-requested-redeem** variant. → *Net Purchase* |
| Reactivation | 20-day gap off successful payment orders, not 30. → *Tableau is the source of truth* |
| % Active | Last purchase within 30 days over the **whole tagged book**, locked included on both sides. → *A locked player still contributes* |
| Locked players | A tagged player contributes to every KPI regardless of lock status. Never add a lock filter to a Goals numerator. |
| Pace | Saturating KPIs use empirical month-shape divisors, not a linear run rate. → *Why Pace is not a straight run rate* |
| Churned / Active Decliners / Milestone Alerts | Removed. Do not re-add without asking. → *Removed: Churned…* |
| Upgrade to Elite | Unreconciled; every tried definition is listed. Do not adopt the 60-day fit. |
| Score = 80 + 20 | KPI points out of 80 plus the manager's 20, total 100. An unscored AM reads `/80`, **never** `/100`. → *Score out of 100* |
| Two score tracks | The 80 and the 20 are separate bars with a gap and rounded ends. Do not merge them. → *Score out of 100* |
| Archive dates | Built by listing the folder, never by date arithmetic. Per audience, so an AM is only offered days their own file exists for. → *Archive calendar* |
| Docs column blank | We can only prove "no ticket names a missing document", never that documents are complete. No green all-clear. → *Pending Redemptions big winner and docs* |

### Two habits that caused the two worst mistakes here

- **Reconcile with the reference file, not by reading numbers aloud.** Paste the
 AM's figures into `data/elite_goals_reference.tsv` and `--goals-only` prints the
 gaps. A 32-account roster leak survived two days because nothing compared the two
 sets automatically.
- **When an instruction and existing code disagree, ask.** Do not write a doc line
 that entrenches the code — that is exactly how three excluded sections stayed in
 the board for days.

---

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python am_daily_dashboard/generate_am_daily_dashboard.py
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27
```

Default report date = **yesterday**.

AM Brief does **not** publish to GitHub Pages. Open the HTML from
`VIP\Elite_Cursor\AM Brief` (a working copy also stays in
`am_daily_dashboard/exports/`). Use `--publish` only if you intentionally need a docs copy.

---

## Output

| Artifact | Path |
|----------|------|
| Canvas | `~/.cursor/projects/.../canvases/elite-am-brief-YYYY-MM-DD.canvas.tsx` (+ per-AM `…-coral/gabriel/lee/rachel.canvas.tsx`) |
| HTML (manager) | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.html` — Overview + AM tabs |
| HTML (per-AM) | `…_elite_am_brief_{coral\|gabriel\|lee\|rachel}.html` — that AM only (no Overview / switcher) |
| JSON | matching `.json` next to each HTML |

HTML is built by injecting the JSON payload into `handoffs/elite_am_brief_web.html` via `canvas_to_html.write_am_brief_html` (not a static table dump).

Standalone refresh from existing JSON:

```bash
python am_daily_dashboard/canvas_to_html.py am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json
```

---

## Sections

### Overview
1. Greeting (once)
2. **Elite & Jackpota** weekday summary + **AM Share Of Elite** (incl. Purchased Of Portfolio)
3. AM Overview metrics (click AM pill → that AM tab only)

### Per AM tab
1. Empowering intro with AM share of Elite + purchased players out of book
2. **Elite Goals** (Coral / Gabriel / Lee / Rachel only — Alon omitted) — current month targets from versioned TSV, MTD actuals, pace, gap, status, weight %, and weighted tracking over the included **80%** KPI weight (manager 20% out of scope). See Goals section below.
3. **Elite & Jackpota** weekday summary (same as Overview)
4. **Morning Checklist** (metric labels jump to sections)
5. **Top 10 Purchasers** — Purchases (#), Top Offer, **Price** (that offer's cost as paid; suffixed `avg` in warning tone if the same offer was bought at more than one amount), **Usual → Ceiling (30D)** price ladder. No Qty / Offer $. See *Top Purchasers price ladder* below
6. **Top 20 · WoW Purchase Gaps** — Daily Elite selection/classify logic, up to 20 per AM
7. **Pending Redemptions** — locked RD ≥ $5,000 created in last **3 days**. Sort: Amount ↓ (default), Won Yesterday ↓, or Oldest first. Created date shows `(Nd ago)` and turns danger-red once a row is within 1 day of the lookback window edge (aging highlight). Then **Won Yesterday** (`· Big Winner` at ≤ −$5,000 GGR), **Docs**, **LTP**, **Hold**, **7D Purchase** — see *Pending Redemptions big winner and docs* below
8. **First-Time Locked RD** — section always shown (empty when none). Ticket column offers a Zendesk draft (review-only), gated by the account's own locked/self-exclusion status
9. **Birthdays · Last 3 Days** — DOB as D/M/Y + Age. Ticket column offers a Zendesk birthday-message draft (review-only), same lock gate
10. **Open Tickets** — LTP, Hold, 7D Purchase + Ticket TIDs link to Zendesk. Sort: LTP ↓ (default), Open Tickets ↓, or 7D Purchase ↓
11. **Locked And Take A Break** — two ways in (`LOCKS_WINDOW_DAYS` / `LOCKS_REVIEW_WINDOW_DAYS`, config.py): still locked **and** (`DATE(locked_at) = report_date`, any reason — the "just happened" feed) **or** (Take a break only, unlock date within 3 days or already passed — regardless of how long ago it started, so a stale overdue break is never missed just because it's no longer "new"). Rows sort by soonest unlock automatically; today/overdue take-a-break rows render in danger tone

---

## Elite Goals

**Targets file (versioned):** `am_daily_dashboard/data/elite_goals.tsv` (copied from the Downloads
`Elite Goals.tsv` source — do not edit/delete the original Downloads file for generator
reproducibility). Year/month selected from `report_date`.

**Weights (locked, sum = 80%):** Daily Avg Purchase 15%, Daily Avg Net Purchase 15%,
Monthly Purchasers 15%, ARPPU 15%, Reactivation 8%, Upgrade to Elite 5%,
% Active from portfolio 7%. Remaining 20% (manager eval) is **out of scope** — the
board shows “% of included 80% weight,” not a 100% corporate score.

**AMs with Goals:** Coral (`coral_s`), Gabriel (`gabriel_e`), Lee (`lee_t`),
Rachel (`rachel_a`). **Alon:** no Goals section / no Goals-bearing per-AM export.

**`% Active from portfolio`** is accounts whose last successful purchase falls
within 30 days of the as-of date, over the **whole tagged book, locked included**
on both sides of the ratio. The 96% target is a deliberate stretch goal.
`portfolioLocked` stays in the payload and on the audit line so the locked drag is
visible without being subtracted. Two earlier answers were wrong and are recorded
below so they are not tried again: unlocked-only, and an invented "eligible"
subset. See *A locked player still contributes to every KPI*.

**`Upgrade to Elite` is the one KPI that does not reconcile** and it is not safe
to score. The board credits the first in-month Elite tag snapshot, giving 53/46/48/26
for Aug 1–17 2026 against the AM's 8/6/7/9 — an order of magnitude apart, so this
is a different set of accounts, not a dating rule. Ruled out on 2026-08-18:
`agent_start_managed_date` in month (38/43/46/24), plus a "never under another AM"
filter (unchanged, 38/43/46/24), and first-ever purchase or account creation
inside the month (0 for everyone).

The AM's reading is "a new user has an AM tag per the date change". The closest
fit is managed date in month **and** account created within 60 days before month
start, giving 7/6/8/4 — right magnitude, and exact only for Gabriel. Windows from
30 to 365 days were swept on both an absolute and a per-account relative basis and
none reproduces all four. **Do not adopt the 60-day fit**; it is tuned to the data,
which is exactly the mistake the "eligible" subset made on % Active. This KPI was
also force-scored at 100% in [`goals_q2_2026/METHODOLOGY.md`](../goals_q2_2026/METHODOLOGY.md),
so it has never had a working data definition here. Waiting on the Tableau field.

### Net Purchase: use the by-requested-redeem variant

`Net Purchase` on this board is the **by requested redeem** variant, confirmed
with the user 2026-08-18 as "the most valid one":

```
purchased − (requested redeem − cancelled) − chargeback − refunds
```

Implemented as `purchased − redeemed_amt_confirmed_locked_pre − chargeback −
refunds` in `goals_mtd_actuals_sql`. That column on
`jackpota_agg.daily_player_revenue_kpis` is the daily precomputed
confirmed + locked + pre_authorized withdraw-request amount — i.e. requested
redeems net of cancelled / declined / failed. Verified exactly equal to those
status sums from `transactional_data.payment_withdraw_money_requests` for all
four AMs over 2026-08-01..16.

**Do not rebuild this from request `status` directly.** `status` is
current-state, so a request that was locked on the report date can be cancelled
later and a status rebuild silently rewrites history. The precomputed daily
column is fixed at its snapshot.

Formula provenance: `net_purchases_byreq` in
`dbt_analytics_mart.abuse_score_daily` /
`dbt_aninditac.int_abuse_score__daily_player_facts` matches
`purchased − redeem_req_minus_cancelled − chargeback − refunds` on 3.67M of
3.67M rows. Neither model can serve this board directly — the mart covers only
~499 accounts and the intermediate stops at 2026-06-02 — but they pin the
formula.

Impact vs the previous paid-redeem variant (Aug 1–16): Coral $33,951 → $24,485,
Gabriel $31,162 → $24,743, Lee $38,205 → $25,576, Rachel $33,093 → $24,969. All
four now read Behind on the $30,000 goal where three previously read On track.
`print_goals_audit` prints the paid-redeem figure on a `(net if paid-redeem
instead)` line, and the payload carries `mtdNetPurchasePaidRedeem` /
`dailyNetPaidRedeem`, so any gap against the Goals sheet stays explainable.

Residual against the user's sheet is ~3% (Coral $24,485 vs $23,703), consistent
with withdraw-request statuses having moved since their sheet was computed.

### Activity windows: the two KPIs do not share one

**Superseded, and the correction matters — an earlier version of this section said
both `% Active` and `# Reactivation` were calendar-month-to-date. That is wrong for
`% Active`, and "fixing" it back to a calendar month breaks Tableau parity.** The
settled definitions, in *Tableau is the source of truth*, are:

| KPI | Window | Scoped to the month? |
|---|---|---|
| `% Active from portfolio` | last purchase **within 30 days of the as-of date** | No — rolling, point-in-time |
| `# Reactivation` | purchase after a gap of **≥20 days**, counted once per AID | Yes — crossings inside the month |

`% Active` is deliberately a rolling rate because that is what the AMs are measured
on, and because it is already a month-end figure it is never extrapolated (see
*Why Pace is not a straight run rate*). Only `# Reactivation` accrues within the
month and therefore paces linearly.

**Window sensitivity is still the first thing to check when an external sheet
disagrees.** Measured for Coral before the definitions were settled, varying only
the window — the absolute values are stale (this used a 594 unlocked denominator and
a 30-day gap, both since corrected), but the spread is the point:

| Window | Purchasers | % of 594 unlocked | Reactivations |
|---|---|---|---|
| MTD Aug 1–16 | 472 | 79.5% | 30 |
| MTD Aug 1–18 | 482 | 81.1% | 32 |
| Trailing 30d to Aug 16 | 530 | 89.2% | 51 |
| Trailing 31d to Aug 16 | 533 | 89.7% | 54 |
| July full month | 554 | 93.3% | 62 |

Reactivation is the most window-sensitive KPI on the board: a trailing 31 days
returned 54 against 30 for the calendar month, an 80% swing from the window alone.
That sensitivity is why the 20-day gap had to be read off the Tableau query rather
than guessed, and why a Reactivation mismatch should always be treated as a window
question first.

### A locked player still contributes to every KPI

**Standing rule (user, 2026-08-18): if a player is tagged to an AM and made any
purchase during the calendar month, his activity counts toward every KPI — being
locked does not remove his contribution.** A lock is an account-status event, not
a statement that the revenue never happened, and the AM should get credit for
work that already landed.

This is why the Goals numerators never filter on `uam_accounts.locked`:
Daily Avg Purchase, Daily Avg Net Purchase, Monthly Purchasers, ARPPU,
Reactivation and Upgrade all include locked accounts by design. **Do not add a
lock filter to any of them.**

`% Active from portfolio` was the one exception. **Its denominator is the whole
tagged book, locked included** — settled 2026-08-18 by comparing against the AM's
own table.

Two wrong answers were tried first, so do not revisit them:

1. **Unlocked only** (Coral 594). Came from an early instruction, contradicted by
 the standing rule above.
2. **An "eligible" subset** — unlocked plus locked accounts that bought this
 month. Invented as a compromise; it inflated % Active by 4–5 points.

The full book reproduces the AM's figures for Aug 1–17 2026:

| AM | Board | Their table |
|---|---|---|
| Gabriel | 83.0% | 82.0% |
| Rachel | 85.2% | 85.0% |
| Lee | 85.6% | 83.0% |
| Coral | 85.5% | not supplied |

`portfolioSize` and `portfolioSizeAll` are therefore the same number now.
`portfolioLocked` still reports the locked count so the drag stays visible, but it
is **not** subtracted anywhere.

### The Goals book is pinned to the report date

Tags are re-snapshotted daily and the books move fast — **Rachel went from 557 to
589 tagged accounts between 2026-08-16 and 08-18**. The Goals query used to read
the newest snapshot available, so an Aug 16 report scored Aug 1–16 activity
against the Aug 18 roster, and re-running the same date on a later day returned
different numbers.

`dashboard_elite_ctes(as_of=...)` now pins the tag snapshot to the newest one on
or before the report date, and `goals_mtd_actuals_sql` passes it. Effect on
Monthly Purchasers for Aug 16: Rachel 429 → 456, Gabriel 476 → 478, Coral 472 →
471, Lee unchanged. Coral's Daily Avg Net Purchase also moved to $23,480 against
the $23,703 on the AM's table — 0.9% off, down from 3.3%.

Pass `as_of` for anything **scored or compared across dates**. Leave it off for
genuinely live sections — Locked/Take A Break and Pending Redemptions are about
what an AM must act on right now, so the current roster is correct there.

#### Pinning takes two filters, not one — `agent_start_managed_date`

Pinning the tag snapshot alone was not enough, and the leak was easy to miss. The
agent resolves as `COALESCE(t.tag_agent_1, e.agent_name)`, and `agent_name` on
`dbt_aninditac.elite` is **current state**. Any account with no tag row on the
as-of date therefore entered through the fallback no matter what the pin said.

On 2026-08-17 that pulled **32 accounts into Rachel's book** that were not hers
that day, and because newly assigned players buy but have barely redeemed, it
inflated her Daily Avg Net Purchase by 11% — more than her gross (7%). Coral and
Lee gained nobody that day and matched the AM's table to the dollar, which is
what made the fault look like a Rachel-specific net-purchase problem rather than a
book problem.

`dbt_aninditac.elite.agent_start_managed_date` is a real assignment date, so
`as_of` now also filters `agent_start_managed_date IS NULL OR <= as_of`. NULL is
kept — those are legacy rows with no date recorded, not late arrivals.

This reproduces **all four AMs' own figures exactly** for Aug 1–17 2026:

| AM | Book | Daily Avg Purchase | Daily Avg Net | Purchasers |
|---|---|---|---|---|
| Coral | 621 | $56,387 | $24,122 | 482 |
| Gabriel | 646 | $43,549 | $23,350 | 482 |
| Lee | 623 | $54,970 | $24,929 | 476 |
| Rachel | 561 | $48,537 | $24,177 | 433 |

The managed date is also what separates two cases that no tag-history rule could
tell apart, so **do not replace it with a "first tagged" proxy**: all 34 disputed
accounts were first tagged on Aug 18, but Gabriel's 2 have a managed date of
Aug 17 (he owned them, they stay) while 28 of Rachel's 32 start Aug 18 (they go)
and 4 have much older dates (they stay). That is why her book lands on 561 rather
than 557 or 589.

Two rules were tried and rejected — do not revisit: excluding accounts first
tagged after the as-of date (drops Gabriel's 2 and breaks him by 4%), and
excluding only reassignments from another AM (all 34 were previously untagged, so
it changes nothing).

**Not** an upgrade definition: `agent_start_managed_date` inside the month gives
38/43/46/24 against the AM's 8/6/7/9. Use it to date *membership*, never to score
upgrades — see the Goals definitions section for everything already ruled out.

### Tableau is the source of truth for Reactivation and % Active

The AMs are measured on a Tableau report, so the board reproduces **its**
definitions rather than inventing parallel ones. Source of truth:
[`elite_reference/Daily_Agg_Per_Player_Query_v1.sql`](../elite_reference/Daily_Agg_Per_Player_Query_v1.sql).

Three things had to change to match it, all settled 2026-08-18:

| | Board before | Tableau / board now |
|---|---|---|
| Purchase source | `daily_player_revenue_kpis.purchased > 0` | `payment_payment_orders` WHERE `success` |
| Reactivation gap | 30 days | **20 days** (`params.churn_period_days`) |
| % Active numerator | bought at some point this month | last purchase **within 30 days** of as-of |

The gap value is the one that mattered. That query's `params.churn_period_days`
is **20**, and its `is_reactivated_today` is "purchased today AND gap from
previous purchase >= churn_period_days". Its inline comments still say 10 —
**they are stale, trust the param.** 20 reproduces Coral's Tableau figure for
Aug 1–16 2026 exactly (55); 30 returns 30.

`% Active` is point-in-time — the share of the book still inside the inactivity
window — not a count that accumulates through the month. So it is **not paced**:
Pace equals Actual, same as a daily average. Coral reads 85.5% against the sheet's
85%. The denominator is the **whole tagged book, locked included** (see *A locked
player still contributes*); an earlier draft of this line said "unlocked book",
which was the first of two wrong answers on that denominator.

Both live in `config.py` as `GOALS_REACTIVATION_GAP_DAYS` and
`GOALS_ACTIVE_LOOKBACK_DAYS`. If that SQL is re-exported, re-check them against
it before trusting any mismatch report.

**Consequence worth reviewing:** on the 20-day definition Coral is already at 55
reactivations by day 16 against a **53/month** goal, pacing to ~107. The 53 goal
lines up almost exactly with the *30-day* pace (58), which suggests the Goals
TSV was calibrated on a 30-day definition while Tableau reports 20-day. The
board now matches Tableau; the goal may need restating.

**As-of / current month:** MTD through `report_date` inclusive (e.g. `--date 2026-08-16`
uses Aug 1–16 only; does not include the next calendar day). First version is
current month only.

| KPI | MTD Actual | Pace (month-end projection) |
|-----|--------|------|
| Daily Avg Purchase | MTD `SUM(purchased) / d` after account/date agg | = actual (a daily average is already a month-end rate) |
| Daily Avg Net Purchase | MTD net / d — Net = **by requested redeem**: purchased − (requested redeem − cancelled) − chargeback − refunds (Elite.MD alternate variant) | = actual |
| Monthly Purchasers | Distinct managed Elite AIDs with purchased > 0 in month through as-of | `MTD / purchasers_shape`, capped at portfolio size |
| ARPPU | MTD purchase $ / Monthly Purchasers | paced monthly purchase $ / paced purchasers |
| # Reactivation | Successful purchase after a gap of **≥20 days** (Tableau `churn_period_days`); once per AID in the month | `(MTD / d) * D` |
| Upgrade to Elite | First Elite `dbt_utils.elite_account_tags` snapshot in month through as-of for accounts **not** Elite on the last snapshot before month start; attributed to `tag_agent_1` on that first in-window snap. Tag history starts **2026-04-08**. | `MTD / upgrades_shape` |
| % Active from portfolio | Accounts whose last successful purchase is **within 30 days** of the as-of date / **unlocked** portfolio | = actual (point-in-time, already a month-end rate) |

`d` = elapsed calendar days from month start through `report_date` inclusive;
`D` = days in month. **Status compares Pace to goal, not MTD.** Achievement per
KPI capped at 100% of goal (same as `goals_q2` `achievement_ratio`);
overperformance does not add extra points.

### Why Pace is not a straight run rate

`(MTD / d) * D` is only valid for KPIs that accrue linearly. Measured on the
four Goals AMs for Jun and Jul 2026, share of the month's final value already
reached by day 16:

| KPI | Jun | Jul | If linear | Treatment |
|---|---|---|---|---|
| Purchase $ | 0.521 | 0.527 | 0.52 | linear run rate is correct |
| # Reactivation | 0.535 | 0.580 | 0.52 | linear run rate is correct |
| Monthly Purchasers | 0.891 | 0.931 | 0.52 | saturates → shape divisor |
| Upgrade to Elite | 0.895 | 0.855 | 0.52 | front-loaded → shape divisor |

A distinct-account count cannot keep growing linearly — it saturates against
the book. Extrapolating it linearly put Coral on pace for **914** purchasers out
of a **621**-player portfolio. Upgrades are front-loaded because the Elite tag
snapshot refreshes early in the month.

So `goals_mtd_actuals_sql` also returns `purchasers_shape` and
`upgrades_shape`: the share of a full month reached by the same *relative* day,
averaged over the two complete prior months, book-wide across the four Goals AMs
(two months per agent is too thin for a per-agent curve). Pace divides MTD by
that share, never goes below MTD, and purchasers are capped at portfolio size.
If a shape falls outside `[0.05, 1.0]` or is missing, that KPI shows no Pace and
Status falls back to MTD vs goal rather than printing a number we do not trust.

ARPPU and % Active are *derived* from the paced components, never paced
directly: at day 16 roughly half the month's spend is in but ~92% of purchasers
are already known, so MTD ARPPU reads about 55% of month-end and made all four
AMs look Behind on a goal they were beating.

**Loader / SQL:** `goals.py` (TSV, pace strategy, weighted score),
`queries.goals_mtd_actuals_sql`, wired in `generate_am_daily_dashboard.py`.
`python -m unittest discover -s am_daily_dashboard` covers the loader, both
shape-paced KPIs, the derived KPIs, and the missing-shape fallback.
`print_goals_audit` prints Goal / MTD / Pace / Status plus the run's shape
divisors for verification against an external sheet.

**Verifying numbers without a full run:**

```
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-16 --goals-only
```

One query, prints the audit table, writes no files (~6s vs ~110s for the whole
board). Use this while reconciling against an external Goals sheet, then do a
normal run once the definitions are agreed.

**The audit diffs itself against the AM's own table.** Paste their figures into
[`data/elite_goals_reference.tsv`](data/elite_goals_reference.tsv) and the audit
grows `Yours` and `Gap` columns. Columns match `elite_goals.tsv` exactly apart
from `day`, so a row copies across with the headers unchanged. Blank cells simply
do not diff, and a missing file is not an error.

`day` must equal the report date. A reference captured on the 16th says nothing
about the 17th — every average and count moves with the elapsed-day divisor, so
the lookup deliberately refuses to match a different day rather than diffing
against the wrong window.

This exists because Aug 2026 was reconciled by reading numbers aloud across
several rounds. That loop did find two real bugs, but it is also why a 32-account
roster leak survived two days: nothing compared the two sets automatically. Keep
the file current and a drift shows up in the same six seconds as the audit.

`goals_reference.py` maps each audit KPI label to its column **and** its unit.
Do not infer the unit from the label — "Monthly Purchasers" contains the substring
"Purchase" and was printed as dollars when it was inferred.

**Per-AM isolation (file-level):** besides the manager multi-AM HTML/JSON/canvas,
the generator also writes:
`YYYY-MM-DD_elite_am_brief_{coral|gabriel|lee|rachel}.html` (+ matching `.json`
and per-AM canvases). Each file contains **only that AM’s** payload — no Overview,
no AM switcher, no other AMs’ data. Mirrored to Elite_Cursor with the manager files.

### Removed: Churned, Active Decliners, Milestone Alerts

**Removed on 2026-08-18 at the user's request. Do not re-add them to this board
without asking.** They had been built and shipped as live sections *after* the
user asked to exclude them, and this file previously carried a note saying they
"remain in the brief even if later feedback asked to drop them" — which is how the
instruction stayed lost. The lesson is the note itself: when an instruction and
existing code disagree, ask, do not write a doc line that entrenches the code.

Each also cost its own BigQuery query on every run, and the milestone one needed a
raised scan cap for a lifetime cumulative window. Removing all three deleted three
queries from the board build.

Churn and Active decliner still exist in `daily_summary`, and `elite-core.mdc`
still owns their definitions, so nothing about the Elite vocabulary changed here.

**The removal was only finished on 2026-08-18 (second pass).** The first pass took
the queries and payload keys out but left the *presentation* behind in all three
implementations, so an AM still saw the sections. Cleaned up: the standalone HTML's
`VIEWS` / `NAV_ORDER` entries, view functions, Morning Checklist tiles and Manager
Dashboard tiles; the canvas's `MorningChecklist` rows and the `AgentBlock` type.
The canvas rows were a live bug — `MorningChecklist` read `focus.churned` and
`focus.activeDecliners`, which the `Focus` type no longer declares and the payload
no longer sends. **When removing a section, grep all three implementations**
(`canvas_parts/`, `handoffs/elite_am_brief_web.html`,
`daily_summary/streamlit_app/am_brief_app.py`), not just the query layer.

---

## Top Purchasers price ladder

Built 2026-08-18 (Batch 8 item 1). The ask was "avg purchase (7D / 30D) + price".
**The average was built, tested against real data, and rejected** — keep it
rejected.

| Column | Definition |
|---|---|
| Price | The top offer's cost **as the player paid it**, `SUM(amount)/COUNT(*)` for that offer on the report date. Cents are kept — an offer is `$899.99`, and rounding to `$900` misquotes it. Suffixed `avg` in warning tone when `offer_unit_min != offer_unit_max`, so a blended price is never passed off as a real one |
| Usual → Ceiling (30D) | `usual_price ×N → ceiling_price`. **Usual** = the price point with the most successful orders in the trailing 30 days, ties going to the higher price. **Ceiling** = the highest price paid **at least twice** in that window |

**Why not an average.** These players buy at 15–25 distinct price points a month,
mixing small top-ups with occasional large offers, so every mean lands in the gap
between the two and names no sellable package. Measured on 2026-08-17:

- AID 445860895 — 1,357 orders / 25 price points. Mean per order **$33**; he
 habitually buys **$19.99** (575 times) and has repeatedly bought **$299.99**.
 Pitching off the mean under-sells him by a factor of ten.
- AID 384245734 — Coral's top at $8,290. Mean per order **$325**, a price he
 essentially never buys; his ladder is **$399.99 ×26 → $899.99**.
- AID 237382747 — averages **$59/day** across 30 days, reading like a minnow, on a
 day he spent **$1,135**.

**Why the ceiling needs two purchases.** A single large order is often a one-off.
AID 449005862 has a $1,000 max but a $299.99 proven ceiling, so planning an upsell
around $1,000 would chase a number he has never repeated.

**A missing `→ ceiling` is meaningful, not missing data**: no higher price point has
been paid twice in 30 days, so there is no proven headroom (e.g. AID 466602384,
`$49.99 ×17`).

`packageFit` is formatted **once**, in `build_package_fit`, precisely so the canvas,
the standalone HTML and the Streamlit app cannot drift on it.

Order level comes from `payment_payment_orders` (successful, non-refunded) because
the KPI view carries no per-order amount and the whole point is which individual
price points recur. This is the order-level reconciliation use that
`bigquery-analytics.mdc` allows, not a revenue source.

---

## Score out of 100 — 80 KPI points plus the manager's 20

Built 2026-08-18 (Batch 10). The user's ask: *"It should be up to 80% and add a 20%
which is my manager appreciation."* Before this, the board showed
`94.4% of the included 80% weight` — a percentage **of** the KPI block, which made
the manager's 20 invisible and read like a mark out of 80.

**The model.** The KPI block is no longer a percentage. It is **points out of 80**
(`kpiPoints` / `kpiPointsMax`, where the max shrinks if a KPI is unavailable — e.g.
75 when Upgrade to Elite's 5 points cannot be scored). The manager awards **0–20**
on top. Together they read out of 100. `weightedTrackedPct` is still in the payload
for back-compat and is what the leaderboard sorts and tones on.

**Input: `data/elite_manager_appreciation.tsv`** (`year, month, agent, points, note`).
Committed with headers only, so nobody starts out scored. Monthly cadence, one row
per AM. Loader is `load_manager_appreciation` / `appreciation_for_month` in
`goals.py`:

- A **missing file is not an error** — the board must render before anybody is scored.
- Points are **clamped to 0–20**.
- A **blank points cell means not scored, not zero.** Awarding 0 is a judgement the
  manager has not made.
- Rows for non-goals agents (e.g. `alon_tish`) are ignored, as in the targets TSV.

Rejected: an editable box in the manager Dashboard saving to `localStorage`. It
lives in one browser, never reaches the AM's own file, and cannot be reproduced for
a past month.

**The unscored state is the whole design, and it must not be "improved".**
`build_score_block` reports an unscored AM as `75.8 / 80`, never `75.8 / 100`.
Presenting `/100` would silently spend the manager's 20 points on the AM's behalf.
Same principle as the Pending Redemptions Docs column: the board only claims what
is true. `managerPointsDisplay` is the literal string `"Pending"` in that state.

**Colour language** (deliberately one new hue, not a fifth status colour):

| Band | Colour | Why |
|---|---|---|
| KPI points earned | Status green / amber / red, on the existing 90 / 70 thresholds | Measured against a goal, so it keeps the tone language the KPI table already uses |
| KPI shortfall | Neutral | The absence of a result, not a second result — red here would double-count the bad news |
| Manager appreciation | **Violet** (`#9386F2`, `theme.category.purple` on canvas) | A judgement, not a measurement. Green would read as "hit a target" |
| Not yet scored | Dashed empty track | Neither 0 nor 20 |

**Two tracks, not one bar.** The KPI 80 and the manager 20 render as separate
tracks with a 6px gap and their own rounded ends (user's explicit request: *"make
sure the 2 progress bars are separated by a few pixels and add border radius at the
end, so it's clear"*). Do not merge them back into a single continuous meter.

- HTML: `scoreMeterHtml` / `scoreLegendHtml`, CSS under `/* Score meter */`.
- Canvas: `ScoreMeter` in `canvas_parts/sections.py`. Uses `theme.stroke.primary`
  for the dashed border — **`theme.border.default` does not exist in the SDK** and
  was a real bug caught here.
- Manager Dashboard leaderboard shows Score, the split meter, and a Manager column.
  It ranks on `totalPctOfMax`, **not** raw points: a scored AM is out of 100 and an
  unscored one out of 80, so ranking by point total would sort every unscored AM
  last by default.

**Streamlit does not render Goals at all** — it never did, so there was no drift to
fix. If Goals is ever added there, it needs this two-track treatment too.

Tests: `ManagerAppreciationTests` in `test_goals.py` covers clamping, blank-means-
unscored, missing file, header-only file, the `/80` vs `/100` denominators, and the
unavailable-KPI case.

---

## Archive calendar and the stable "latest" link

Built 2026-08-18 (Batch 10), answering *"could you build an internal calendar so
each day they can go back to the previous and see the report?"*

**The problem it solves.** Dated files were already never overwritten, so history
existed (8 manager dates back to 27 July). But there was no index, no date control,
and **no dateless filename**, so a bookmark died overnight and an AM had to know the
date and pick from a flat folder growing by 10 files a run. Per-AM files only began
16 Aug, so an AM could reach two days of their own history against the manager's
three weeks. The user's decision: **start history fresh once the tool is ready** —
do not backfill.

**Two pieces:**

1. **Dateless latest copies.** `elite_am_brief.html` and
   `elite_am_brief_<slug>.html`, rewritten every run and mirrored to Elite_Cursor.
   These are what people bookmark and open; the dated files are the archive.
2. **Month calendar in the topbar.** `archive_entries(slug, report_date)` in the
   generator **lists the export folder** and embeds `report.archive` as
   `[{d, f}, …]`; the HTML renders a month grid where only those days are
   clickable, with prev/next bounded by the months present.

**Why it scans the folder instead of computing dates.** The board is not generated
every day — Fri/Sat are skipped and runs get missed (the current archive has a real
3–5 Aug hole). Any date arithmetic would offer a day whose file does not exist and
produce a dead link. Navigation is a plain sibling-file `location.href`, so the
archive works from a copied folder or network share with no server.

`slug` selects the audience: `""` is the manager file, otherwise that AM's own
files. **An AM must never be offered a date their own file does not exist for** —
this is why the archive list is built per audience rather than shared.

Calendar state lives on `app.calOpen` / `app.calMonth`; the outside-click and
Escape handlers are bound **once on `document`**, not per render.

---

## Pending Redemptions big winner and docs

Built 2026-08-18 (Batch 8 item 2). Five columns after Created:

| Column | Definition |
|---|---|
| Won Yesterday | The player's report-day win, `−(profit − loss)` on `daily_player_revenue_kpis`. GGR is house-side, so a player win is a **negative** GGR day and this flips the sign. A losing day reads `—`, never a negative win. At ≥ `BIG_WINNER_MIN_PLAYER_WIN` ($5,000) the cell adds a danger-tone `· Big Winner` label |
| Docs | `_zendesk_missing_doc_tag` from `wow_drop_analysis/wow_drop_reason.py` — the same wording the WoW handoff uses ("Needs Recent Acceptable POA", "Needs KYC / Verification Document"). Blank when nothing is flagged |
| LTP / Hold / 7D Purchase | Account context for judging a held withdrawal, same formatters as Open Tickets |

**The all-clear is blank on purpose, and this is not a cosmetic choice.** The
source can only prove "no open ticket names a missing document" — it cannot prove
the documents are verified complete. A green "All docs OK" would be a claim the
data does not support, and an AM could repeat it to a player waiting on a
withdrawal. Blank keeps the eye on the rows that actually need work. Do not
"improve" this into a positive badge.

**Big Winner outranks the ageing highlight for row tone.** A held withdrawal from
someone who just won five figures is the row to open first, so it takes danger
tone even when the row is not near the lookback edge.

Both fields cost **no extra query**: the GGR day joins inside
`locked_rd_over_5k_sql` against the same locked-RD set, and the docs/LTP/Hold/7D
values reuse the `enrich_aids_sql` result the board already fetches for Open
Tickets — `rd5k_raw`'s AIDs were simply added to that one batch.

Verified on 2026-08-17: 6 pending rows, 1 flagged. AID 378858687 shows a $9,910
win against a BigQuery day GGR of **−9,910.02**; AID 373278918 wins $1,387 and is
correctly *not* flagged; AID 300286239 had a positive GGR day and reads `—`.

---

## Top 20 filters (same as Elite Daily Decline)

1. Search — name, AID, agent, reason…
2. Agent Select — Overview only (AM tabs are pre-filtered)
3. Sort — Urgency + gap | Prior purchase ↓ | Lifetime purchase ↓ | WoW gap ↓
4. Reason pills — All reasons + distinct reasons
5. `Showing N of M` when filters active; Total row on prior purchase

---

## Sources

| Data | Source |
|------|--------|
| Book / Agent | `dbt_aninditac.elite` + latest `tag_agent_1` |
| Purchase $ | KPI agg by account/date |
| Offers | `payment_payment_orders` + `payment_offer_templates` |
| DOB / Age | `uam_account_personal_info.date_of_birth` (skip 1900-01-01); age = `DATE_DIFF(report_date, DOB, YEAR)` |
| Pending RD | `payment_withdraw_money_requests` status `locked`, amount ≥ 5000, created in last 3 days |
| Zendesk | Open tickets; `ARRAY_AGG` of ticket IDs (TIDs) |
| Locks | `uam_accounts.locked` / `lock_reason` / `locked_at` |

---

## Design

Matches Elite Daily Decline canvas: Looker AID links, `ReasonCell` / `ActionCell` / money cells, `TicketDraftModal`, filter bar, striped sticky tables. Title **Elite AM Brief**; subtitle date only (`{Weekday} {DD Mon YYYY}`).

Standalone HTML uses the same interactive shell as the canvas (Overview + AM pills, checklist jumps, Top 20 filters/ticket draft) — not a static table dump.

**Filters only where needed.** Search box stays on **Top 10 Purchasers**, **Top 20 · WoW Purchase Gaps**, and **Open Tickets** (per user correction: Top 10 is kept after all). Removed from Pending Redemptions, First-Time Locked RD, Birthdays, and Locked/Take A Break — each is typically well under 10 rows per AM tab, so a search box added a step with no payoff. Controlled by a `showSearch` option on `SearchableTable` (canvas) and `searchableSection` (HTML) — default `true`, set `false` at the 4 call sites above.

**Compact tables.** Morning Checklist (2 columns) and Top 10 Purchasers (6 columns, several short) used to stretch to the full panel width like every other table, leaving large gaps between sparse columns ("too wide" feedback). Both now size to their content instead: canvas passes `style`/`tableStyle={{ width: "max-content", maxWidth: "100%" }}` directly to `Table` / through `SearchableTable`; HTML adds a `.compact-frame` class (`frameClass` option on `tableHtml`, `compact: true` option on `searchableSection`) that overrides the default `width: 100%` frame and the table's `min-width: 100%`. Every other table keeps stretching to fill the panel — this is opt-in per call site, not a global change.

**Known architecture gap.** The canvas (`am_brief_canvas.py` + `canvas_parts/`) and the standalone HTML (`handoffs/elite_am_brief_web.html`) are two independently hand-written implementations of the same UI (TSX vs. template-literal JS). Any future section, column, or filter change must currently be applied in **both** places by hand — there is no shared rendering layer. Not addressed in Batch 1 (would need a larger unification); tracked in the Roadmap below.

**Ticket drafts, review-only.** Three families now offer a Zendesk ticket draft — Top 20 · WoW Purchase Gaps (`wow_drop_analysis/ticket_draft.py`), and First-Time Locked RD + Birthdays (`am_daily_dashboard/am_brief_ticket_drafts.py`). All three: agent edits Subject/Message in the modal, copies, opens Zendesk, sends manually — nothing is auto-created or auto-sent. All three are gated by the elite-core rule "never recommend retention outreach for a locked or self-excluded account" — checked via `uam_accounts.locked` / `lock_reason` before the draft is offered (`outreach_lock_gate` in `am_brief_ticket_drafts.py`; WoW Gaps has its own equivalent check baked into its reason-code classification). When disabled for this reason, the Ticket column shows the lock label (e.g. "Locked — Self-exclusion") instead of a blank `—`, so the agent can see why. WoW Gaps drafts additionally get the row's literal Reason + Recommendation text appended as an internal, agent-only note below a separator in the message body — not sent to the player.

---

## Roadmap / Backlog

Living backlog for the AM Brief, reviewed with the user before starting the next batch. Each batch should leave the brief working exactly as before unless a change was explicitly asked for and mocked first.

### Batch 1 — Editability refactor (done, two items deliberately deferred)

- [x] Split `am_brief_canvas.py` (1,047 → 201 lines) into `canvas_parts/cells.py`, `canvas_parts/tables.py`, `canvas_parts/sections.py` (`AgentPanel` — the actual per-section composition). Verified byte-identical render output before/after.
- [x] Filters only where needed (see Design above), applied to both canvas and HTML.
- [x] Thresholds consolidated into `config.py`: `PENDING_RD_MIN_AMOUNT`, `PENDING_RD_LOOKBACK_DAYS`, `BIRTHDAYS_LOOKBACK_DAYS`, `LOCKS_WINDOW_DAYS`. Verified identical generated SQL / selection logic for current values.
- [ ] Query/build "registry" for `generate_am_daily_dashboard.py` — **deferred**. `queries.py` already has one function per section and `build_payload` is linear/readable; a formal registry would add abstraction without a clear current payoff. Revisit if sections start being added/removed often.
- [ ] Unify canvas vs. HTML rendering (see architecture gap above) — not scoped into Batch 1; needs its own sizing.

### Batch 2 — Distribution + automation (not started)

- Confirm current hosting reality for AM-facing access
- Per-AM shareable link that still includes Overview (not stripped) — AM Brief already shows the Overview + AM tab switcher together; revisit if a stripped-down per-AM-only link is built
- Scheduled automated daily generation (no manual script run)
- Slack ping when the brief is ready

### Batch 3 — Section polish + new ticket drafts (done)

Requested directly on the build-map canvas's per-section "Requested change" column (`elite-am-brief-build-map.canvas.tsx`, outside this repo under the Cursor projects folder); scoped and mocked in `elite-am-brief-batch3-mock.canvas.tsx` before implementation.

- [x] Renamed "Purchase / Book" → "Purchased Of Portfolio" (AM Share Of Elite + AM Overview tables, canvas + HTML)
- [x] Top 10 Purchasers: search box restored (kept after all, per user correction to the Batch 1 filter removal)
- [x] Open Tickets: sort control — LTP ↓ (default), Open Tickets ↓, 7D Purchase ↓
- [x] Pending Redemptions: sort control — Amount ↓ (default), Oldest first — plus an aging highlight (danger tone, `(Nd ago)`) once a row nears the lookback window edge
- [x] Top 20 · WoW Purchase Gaps ticket drafts: literal Reason + Recommendation text now appended as an agent-only internal note in the message body
- [x] First-Time Locked RD: Zendesk ticket draft (new — `am_brief_ticket_drafts.py`), gated by account locked/self-exclusion
- [x] Birthdays: Zendesk ticket draft (new, same module + gate)
- [x] Locked/Take A Break: rows auto-sort by soonest unlock; today/overdue take-a-break rows render in danger tone — no new filter control added (kept to "filters only where needed")
- [x] Regenerated + verified end-to-end (BigQuery → canvas + HTML), JS-syntax-checked the HTML template

### Batch 4 — Layout fixes + Locks completeness (done)

Requested directly on the build-map canvas's per-section "Requested change" column, plus a product gap the user resolved after seeing the Batch 3 mock.

- [x] Morning Checklist: fixed "too wide" — table now sizes to content instead of stretching the panel
- [x] Top 10 Purchasers: fixed "too wide" — same fix, search box kept
- [x] Locked/Take A Break: added a second, age-independent path (`LOCKS_REVIEW_WINDOW_DAYS`) so an overdue take-a-break surfaces and gets flagged red even if the lock started long before report_date — closes the gap identified in the Batch 3 mock, where the danger-tone highlight could never actually trigger under the 1-day-only window. Verified against real data: 2 accounts (overdue by 4 and 95 days) now surface that were previously invisible to this section.
- [x] Regenerated + verified end-to-end (BigQuery → canvas + HTML), JS-syntax-checked the HTML template

### Batch 5 — Content evolution (built, then reverted 2026-08-18)

Churned (7d), Active Decliners and Milestone Alerts were built as live sections
and then **removed on 2026-08-18**, because the user had asked to exclude them and
they shipped anyway. Kept here as a record of what happened rather than deleted,
since the mistake is the useful part. See *Removed: Churned, Active Decliners,
Milestone Alerts* above before considering any of it again.

- [x] Elite Goals — targets, MTD actuals, pace, weighted tracking (kept; the one
  part of Batch 5 that survives)
- [~] **Churned (7d)** — reverted. Trailing-7d zero purchase, elite-core Churn
- [~] **Active Decliners** — reverted. Bought in trailing 7d but less than prior 7d
- [~] **Milestone Alerts** — reverted. Lifetime purchase crossing a tier within 30d,
  from a per-account cumulative running total

### Batch 6 — Interactivity (not started)

- Mark an item actioned/dismissed (needs new state storage — not derivable from BigQuery alone)
- Drill-down from a summary row into `wow-drop-reason-analysis` / `purchase-lookup`
- Scheduled/future ticket delivery for Locked/Take A Break unlock reminders (raised alongside the Batch 3 Locks request; needs new backend scheduling, not just a UI change — deferred out of Batch 3)

### Batch 7 — UI/UX overhaul (requested 2026-08-18, not started)

Requested by the user right after the Goals reconciliation landed. Four asks,
verbatim intent preserved so this can be picked up after the Goals work:

1. **Left sidebar navigation.** Stop rendering all 11 sections on one long
 page. Group them under section headings in a persistent left menu and show
 one section at a time.
2. **Manager dashboard.** A main dashboard with the roll-up numbers that only
 the user can open — not visible in the AM-facing files.
3. **Real design pass.** Current look is flat and lifeless. Wants something
 alive and team-appropriate, with proper **inline SVG icons** — not emoji and
 not a CDN icon font (files are opened from OneDrive and must work offline).
4. **Pagination on large tables.** Page-size control (25 / 50 / 100) plus page
 navigation. **Re-check whether this is still worth building:** the three
 sections that motivated it (Churned ~200–265 rows/AM, Active Decliners
 ~150–177, Milestone Alerts ~77–80) were removed on 2026-08-18. Every
 remaining section is far smaller — Open Tickets is the largest and Top 10
 Purchasers is capped at 10.

Scope note: all of this lives in `handoffs/elite_am_brief_web.html`. The
`canvas_parts/` TSX canvas and `daily_summary/streamlit_app/am_brief_app.py`
are separate hand-written implementations of the same UI (see *Known
architecture gap*) and will drift further unless deliberately re-synced.

### Batch 8 — Team feedback, section content (items 1–2 done)

Five asks the user collected from the AM team and read out on 2026-08-18, to be
worked **one at a time** with agreement on each before building. Their intent is
preserved here rather than paraphrased into a spec, because several still need a
decision from them. Their item 1 was Elite Goals, which is done.

**Read the GGR sign convention first.** `Elite.MD` defines GGR as `profit − loss`
from the house's side, so a **player** big win is a **negative** GGR day. "−5K GGR"
below means the player won ~$5,000, not that they lost it. Getting this backwards
inverts both big-winner features.

1. [x] **Top Purchasers — price and package fit.** Done 2026-08-18. Shipped as
 **Price** + **Usual → Ceiling (30D)** in all three implementations. The requested
 7D/30D *average* was built first, checked against real data, and dropped because a
 mean names no sellable package; the user asked for something that actually supports
 an offer decision. Momentum and cadence were designed, shown, and deliberately
 left out to keep the section narrow. Full reasoning and the rejected variants:
 *Top Purchasers price ladder* above.
2. [x] **Pending Redemptions — big winner and missing-docs status.** Done
 2026-08-18. Shipped in all three implementations as five columns — **Won
 Yesterday** (with a `· Big Winner` danger-tone label at ≤ −$5,000 GGR,
 `BIG_WINNER_MIN_PLAYER_WIN` in `config.py`), **Docs**, plus **LTP / Hold / 7D
 Purchase** for the account context the user asked to see alongside the flag. New
 sort: Won Yesterday ↓. Big Winner outranks the ageing highlight for row tone. The
 all-clear docs case renders **blank** by the user's choice — see *Pending
 Redemptions big winner and docs* below for why that is the honest reading.
3. **Big Winners ≥ $20K — new section.** Players at ≤ −$20,000 GGR on the past day,
 with how much they redeemed and which game the big win happened on. **Scope settled
 2026-08-18:** non-Elite players **are** included, and they appear in **every AM's
 own view**, not just the manager Overview — the user's reasoning is that handling a
 $20K winner is part of every AM's daily job and they know when to address it. This
 is the **only** section on the board that reaches outside the Elite book, so the
 non-Elite rows must be labelled as such, and no other section may copy the wider
 filter. Elite rows stay scoped to that AM's book.
4. **Last win above 1K SC — date plus redeemed yes/no.** Per player. Confirm whether
 this is a column on an existing section or its own.
5. **Open Tickets — weighted prioritisation.** Four weights given verbatim:
 lifetime hold 25%, lifetime NGR 20%, **lifetime purchase 20%**, 30-day purchase
 25%. That sums to **90%**. *Settled 2026-08-18:* nothing is missing — **normalise
 the four to 100%** (27.8 / 22.2 / 22.2 / 27.8) so the priority score reads out of
 100. Unlike Goals, which deliberately scores out of its included 80%, this one is
 normalised. (An earlier note here recorded only three of the four and put the gap
 at 30%; the lifetime-purchase weight was dropped in transcription.) Still open: the
 user wants ticket **subjects or topics** shown next to the weight and asked to
 define that set together.

### Batch 10 — Score out of 100 + archive calendar (code-complete, unverified)

Raised by the user mid-Batch-8 on 2026-08-18 and built the same day. Design was
mocked and approved first (`handoffs/elite_am_brief_goals_8020_proposal.html`, also
mirrored to Elite_Cursor; canvas twin
`canvases/elite-am-brief-goals-8020-and-archive.canvas.tsx`). The user approved with
one refinement — separate the two bars by a few pixels and round each end.

- [x] `MANAGER_APPRECIATION_MAX = 20`, `load_manager_appreciation`,
  `appreciation_for_month`, `build_score_block` in `goals.py`
- [x] `data/elite_manager_appreciation.tsv` committed with headers only
- [x] `build_agent_goals_block(..., appreciation=)` emits a `score` block
- [x] Generator loads the month's appreciation, prints who is scored, adds
  `goalsMeta.managerAppreciationMax`
- [x] HTML: two-track meter + legend on the Goals card, the Goals view and the
  manager leaderboard (new Manager column, ranked on `totalPctOfMax`)
- [x] Canvas: `ScoreMeter` + `score` on the `AgentBlock` goals type
- [x] `archive_entries` / `with_archive`, dateless latest files, topbar month
  calendar with outside-click and Escape
- [x] 8 new unit tests (38 total, passing); HTML JS syntax-checked
- [ ] **Run the generator and verify end to end** — never executed after these edits
- [ ] Confirm with the user whether the AM Brief joins the Sun–Thu 10:00 task
- [ ] Retention/pruning of dated files — proposed 60 days, never answered

**Still unanswered by the user** (asked, superseded by "looks good" plus the two
refinements, so treat the recommendation as provisional and confirm before relying
on it): whether each AM sees their own manager score in their own file
(recommended and built as **yes** — it appears on their card), points vs a scaled
percentage (built as **points out of 20**), scheduling, and retention.

### Batch 9 — Game intelligence (approved, not started)

Both approved in principle on 2026-08-18; neither has been built or mocked.

- **Trending games board.** Book-wide rather than per-AM, Top 10, with a minimum
 player count so a game with three players cannot top the week-over-week percentage
 table. Design the floor as a `config.py` constant.
- **Dormant favourite game flag.** Flag a player who stopped playing a previously
 favourite game **only when they had a net loss on that game** — the user's own
 refinement, on the reasoning that a player who moved on after losing is a
 different story from one who simply rotated. Do not flag net-positive rotations.

### On hold — needs something from the user

- **Zendesk auto-create.** Agreed in principle: create tickets automatically as
 **internal notes only**, and for the **AM Brief only** — not the WoW handoff, and
 never auto-sent to a player. **Blocked on API credentials**, which the user will
 supply. Until then everything stays review-only draft-and-copy. Never commit the
 credentials (`elite-core.mdc`).
- **"One month since AM assignment" rule.** The user asked for a positive-touch
 trigger at one month from assignment, but the definition was never settled: does a
 reassignment reset the clock, is it a window or the exact day, and does it produce
 a ticket draft. **Useful finding from the Goals work:** `dbt_aninditac.elite`
 carries `agent_start_managed_date`, which is the assignment date this rule needs —
 the same column that fixed the book pinning. Ask the three questions, then build
 off that column.
