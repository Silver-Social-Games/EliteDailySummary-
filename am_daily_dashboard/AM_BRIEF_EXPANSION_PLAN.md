# AM Brief — 7-feature expansion plan

**Canonical copy in the Elite repo** (agents read this path; the Cursor plan UI copy
may not resolve in new chats).

**Handoff:** paste block at end of this file. **Rollback:** section below.

**Status todos:** Phase 0 ✅ → B ✅ (Goals history, 2026-09-01) → C/D/E → F → G → H
(check off in chat as you go).

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

## New-chat handoff (paste this)

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

For feature specs (SQL, views, peer mode, calculator): read sections **Phase 0** through **7** in [`AM_DAILY_DASHBOARD.md`](AM_DAILY_DASHBOARD.md) after implementation updates, and the planning chat; this file holds rollback, build order, and handoff.
