# AM Brief — 7-feature expansion plan

**Canonical copy in the Elite repo** (agents read this path; the Cursor plan UI copy
may not resolve in new chats).

**Handoff:** paste block at end of this file. **Rollback:** section below.

**Status todos:** Phase 0 ✅ → B ✅ (Goals history, 2026-09-01) → C ✅ (Anniversary,
2026-09-01, trailing window) → D ✅ (Birthday Gift, this-month birthdays +
criteria, 2026-09-01) → E ⛔ DROPPED from board (Responsiveness parked
2026-09-01; dormant helpers kept for re-add) → F ✅ (Coverage board LIVE default
`PEER_BOOK_MODE = True`, tabs = AMs with own brief so Alon drops, per-AM archive
history, 2026-09-01) → G → H (check off in chat as you go).

---

## Rollback and safe baseline (do before any code changes)

Exports are **not in git**. A bad regen overwrites working JSON even when UI code is fine. Use **three layers** so you can return to today's working board at any time.

### Layer 1 — Code (git)

| Action | Command / note |
|---|---|
| Create a branch | `git checkout -b am-brief-expansion` (stay off main until QA passes) |
| Baseline commit | Commit current workshop state **before** Phase 0 edits; record hash in chat |
| Roll back code only | `git checkout main -- am_daily_dashboard/` (or reset branch) |
| Roll back one file | `git checkout main -- path/to/file` |

Code rollback alone does **not** restore exports or Elite_Cursor HTML.

### Layer 2 — Report data (`exports/verified/`)

Already built in: every `verify_brief.py` PASS copies JSON to `am_daily_dashboard/exports/verified/`.

**Baseline today (run once before expansion):**

```bash
cd "c:\Users\Owner\Downloads\Elite"
python am_daily_dashboard/verify_brief.py --date 2026-08-31
```

**Restore a good day after a bad regen:**

```bash
python am_daily_dashboard/verify_brief.py --date 2026-08-31 --restore-verified
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-31 --html-only --cursor-audience manager
```

**Never** full-regen a verified date unless you intentionally want fresh BQ numbers.

### Layer 3 — Elite_Cursor filing cabinet

Copy `VIP\Elite_Cursor\AM Brief` → `VIP\Elite_Cursor\AM Brief_baseline_2026-09-01` before coding.

### Layer 4 — Feature flags

| Flag | Safe default |
|---|---|
| `PEER_BOOK_MODE` | `False` until Phase F QA |

---

## Model choice — per phase

| Phase | Model |
|---|---|
| Baseline | You (or Composer) |
| 0, B | **Thinking** (Sonnet thinking / Opus) |
| C, D | **Fast** (Composer) |
| E | **Thinking** |
| F, G | **Thinking+** (Opus for F if available) |
| H | **Fast** |

---

## Principles

- One section at a time: `queries.py` → `payload_builders.py` → `web/src/views/*.ts` → tests → `verify_brief.py`.
- HTML is canonical; never read `exports/` JSON in agent tools.
- Reuse `enrich_aids_sql` batch where possible.
- Thresholds in `config.py` only.

---

## Phase 0 — Shared foundations

- `config.py` keys: `TICKET_INACTIVITY_DAYS`, `BIRTHDAY_GIFT_*`, `ANNIVERSARY_*`, `PEER_BOOK_MODE`
- `verify_brief.py` helpers for new sections
- `snapshot_baseline.py` (optional Phase 0 deliverable)
- Update `AM_DAILY_DASHBOARD.md` routing table

## 1. Goals — final month history

- `data/elite_goals_history.json` + `goals_history.py` close on month-end
- UI in `views/goals.ts` and `views/team.ts`
- Backfill Aug 2026 from `2026-08-31` verified JSON

## 2. Responsiveness — 90 days no ticket activity

- `ticket_inactivity_sql` + `build_responsiveness_section` + `views/responsiveness.ts`

## 3. Birthday Gift Report — eligible players

- Hold ≥ 50%, 30D purchase ≥ $4K; refresh weekly (Sunday)
- Separate from Birthdays · Last 3 Days

## 4. Peer AM tabs (coverage)

- `strip_payload_for_am_peers`: all 4 AM tabs; Goals only on home AM
- `PEER_BOOK_MODE` flag; highest risk — ship last before Slack go-live

## 5. One-month anniversary

- `agent_start_managed_date + 30 days`; replace comingSoon anniversary view

## 6. Bonus Calculator — Inbound (green)

- Daily lookup JSON + `bonus_calculator.py` / `bonusCalc.ts` (V5 NGR rules)

## 7. Slack + backward history

- Archive calendar already works; improve Slack DM copy; enable scheduled task

---

## Build order

| Order | Feature | Model |
|---|---|---|
| A | Phase 0 | Thinking |
| B | Goals history | Thinking |
| C | Anniversary | Fast |
| D | Birthday Gift | Fast |
| E | Responsiveness | Thinking |
| F | Peer book mode | Thinking+ |
| G | Bonus Calculator | Thinking |
| H | Slack onboarding | Fast |

Ship B → C → D → E before F. Enable F + H together for AM rollout.

---

## Decisions locked

- Calculator: Inbound V5 NGR (green section in Excel)
- AM coverage: peer tabs; Goals hidden on other AMs
- Birthday Gift: new section; keep 3-day Birthdays
- History: archive calendar + Slack instructions

---

## Original expansion handoff (superseded — use "Session 2026-09-28" below)

```
@elite-am-brief — execute AM Brief expansion plan (7 features).

Read the plan first:
  am_daily_dashboard/AM_BRIEF_EXPANSION_PLAN.md
(Rollback: same file, section "Rollback and safe baseline")

BASELINE (do not overwrite without restore):
- Last verify PASS: 2026-08-31
- Open: VIP\Elite_Cursor\AM Brief\elite_am_brief.html
- Recent shipped: Top 10 LTP + Hold (plain LTP text); Aug 31 full regen PASS

Before coding:
1. git checkout -b am-brief-expansion
2. python am_daily_dashboard/verify_brief.py --date 2026-08-31
3. Copy Elite_Cursor\AM Brief → AM Brief_baseline_2026-09-01

Restore if broken:
  python am_daily_dashboard/verify_brief.py --date 2026-08-31 --restore-verified
  python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-08-31 --html-only --cursor-audience manager

Build order: Phase 0 → B Goals history → C/D/E → F peer mode → G calculator → H Slack
Flags: PEER_BOOK_MODE=False until F is QA'd
Model: Thinking for Phase 0 + B (see plan "Model choice — per phase")

Do not read exports/ JSON in agent tools — use verify_brief.py only.
```

---

## Session 2026-09-28 — shipped + open (current handoff)

**Shipped on `am-brief-expansion` (not pushed):**

- `ca42ac1` — fixed AM trend colours (Coral red, Gabriel blue, Lee green, Rachel purple, Alon orange); **1 Month Anniversary · Last 3 Days** label; **This Month Hold %** on the Jackpota / Elite WoW panels (`purchase_trend_sql` `net` → `report.purchaseTrend.holdMtd`); **run-date labels** (board shows the data date + 1; files, queries and archive keys stay on the data date); Slack header shows the run date.
- `64bc940` + `f205024` — Purchase Trends daily chart: **one left $ axis for every series, heights proportional, never a second axis**; default **Elite + Jackpota for every audience**; 280px; no axis title or legend; a dot on every day; **values on hover only** in a readout strip above the plot (CSS `:hover`, no JS); small end labels with leader lines. Static per-day labels and a split axis were both tried and rejected.
- `0983cfd` — no subtitle on Team Goals ("Your targets, Elite Portfolio" removed); **AM Overview** table removed from the Manager Dashboard (`overview` still built, do not re-add); calendar button shows only the date, bold black.
- Every saved brief refreshed via `--html-only --date 2026-09-27 --cursor-audience manager`. Coral / Gabriel / Lee / Rachel copies in `Elite_Cursor\AM Brief\<AM>\` carry the new shell.

**Last verify PASS:** 2026-09-27 with `--render-check` (2026-09-26 also PASS after a full regen with `holdMtd`). **Tests:** 293 Python + 29 jsdom, all green.

- Follow-up commit (same day) — **hero sparkline on one shared $0 scale** (`sparklineSvg(lines, { shared: true })`; jsdom test asserts the smaller series never draws above its parent and its peak sits below); **Jul 2026 Goals History = 100%** for Coral / Gabriel / Lee / Rachel + team in `data/elite_goals_history.json` (`source: manual-100`, goals from the July TSV rows, actual = pace = goal); SKILL Manager Dashboard line; `print_handoff.py` baseline. Verify 2026-09-27 `--render-check` PASS after `--html-only`.

**Not done (skipped by user):** keeping or hiding the "Monday" archive entry. It is Sunday 27 Sep's full data shown on the run date. Leave it.

### Open work — done 2026-09-28 (kept for reference)

No open items from this session. Next feature work: see **Build order** above.

1. **Hero sparkline never crosses.** In `web/src/charts.ts` `sparklineSvg`, add a `shared` option: `lo = 0` and one common `hi` across all lines. Today each line is scaled to its own min–max, so Elite can draw above Jackpota. `components.ts::trendHeroPanel` passes `{ shared: true }` (manager: Jackpota over Elite; AM file: Elite over own book). Add a jsdom test that Elite's y is at or below Jackpota's at every point of the hero `svg.spark`.
2. **July 2026 Goals History = 100% (user decision, no BigQuery).** The `exports/2026-07-31` JSON predates Goals, so `goals_history.py --close` writes nothing. Instead, write a `2026-07` entry into `data/elite_goals_history.json` with a one-off snippet, same shape as `2026-08`: `monthLabel "Jul 2026"`, `closedAsOf "2026-07-31"`, `source "manual-100"`; agents Coral / Gabriel / Lee / Rachel (tags `coral_s` / `gabriel_e` / `lee_t` / `rachel_a`) plus `team`, each `kpiPoints 80`, `kpiPointsMax 80`, `kpiPct 100`, `weightedTrackedPct 100`, and `portfolioSize` / `activePlayers` / `mtd*` null. The 7 KPI rows use August's keys, labels and weights; goals come from the `elite_goals.tsv` July rows (AM: $49,000 · $28,000 · 509 · $2,952 · 49 · 49 · 95.0%; team: $200,000 · $116,000 · 2,100 · $2,952 · 200 · 200 · 95.0%); actual = pace = goal, gap 0, `On track` / `success`. If the user pastes real July actuals, use them for Actual only.
3. Ship: `npx tsc --noEmit` → `node am_daily_dashboard/web/build.mjs` → `npm test` (tests_js) → `python -m unittest discover -s am_daily_dashboard` → `--html-only --date 2026-09-27 --cursor-audience manager` → `verify_brief.py --date 2026-09-27 --render-check`. Update the SKILL hero line and `print_handoff.py` (test baseline 293, the commits above). Commit on `am-brief-expansion`, with no push.

### New-chat handoff (paste this)

```
@elite-am-brief — branch am-brief-expansion.
Read am_daily_dashboard/AM_BRIEF_EXPANSION_PLAN.md section "Session 2026-09-28" (all open work done).
Last verify PASS: 2026-09-27 (--render-check). Tests: 293 Python + 29 jsdom green.
Do not read exports/ JSON or HTML — use verify_brief.py. PowerShell: chain with ; not &&.
July Goals History = 100% for every AM + team, entered by hand — do not regenerate 2026-07-31.
Commit on am-brief-expansion, do not push.
Open: VIP\Elite_Cursor\AM Brief\elite_am_brief.html
```

For feature specs (SQL, views, peer mode, calculator): read sections **Phase 0** through **7** in [`AM_DAILY_DASHBOARD.md`](AM_DAILY_DASHBOARD.md) after implementation updates, and the planning chat; this file holds rollback, build order, and handoff.
