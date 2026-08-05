# Elite Daily Summary

Morning reports for the **Elite** managed book — platform + Elite performance, Top 20 player comparison, reasons, and agent recommendations. Runs automatically Sun–Thu at 10:00 Israel time.

---

## What you get

Each run produces:

- **Markdown** — shareable summary text
- **HTML** — open in Chrome, same layout as the Cursor canvas
- **Canvas** — interactive view in Cursor (search, filters, Zendesk ticket draft)

**Daily** (Mon–Thu): one day vs the same weekday last week.  
**Weekend** (Sunday): combined Thu + Fri + Sat in one report.

---

## Quick start

### 1. Install

```bash
cd path\to\EliteDailySummary
pip install -r requirements.txt
```

### 2. Add BigQuery credentials

Either:

- Set environment variable `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON path, **or**
- Place your key at `c:\Users\Owner\Downloads\key.json.json` (default used by the scripts)

You need read access to `silver-social-games-data` (EU).

### 3. Run today's report

```bash
python daily_summary/generate_morning_elite.py
```

That's it. The script picks the right report type based on today's weekday.

### 4. Open the result

```bash
# Daily example (replace date)
start daily_summary\daily_summaries\2026-07-12_elite_daily_summary_canvas.html

# Weekend example
start daily_summary\daily_summaries\2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html
```

Reports are saved under `daily_summary/daily_summaries/`.

---

## When does it run?

| Day | What generates | Covers |
|-----|----------------|--------|
| **Sunday** | Weekend bundle | Prior Thu, Fri, Sat |
| **Monday** | Daily | Sunday |
| **Tuesday** | Daily | Monday |
| **Wednesday** | Daily | Tuesday |
| **Thursday** | Daily | Wednesday |
| **Friday / Saturday** | Nothing | Thu–Sat wait for Sunday |

Thursday is only in the **Sunday weekend report**, not as a standalone daily — by design.

### Automate on Windows (once)

Set Windows timezone to **Jerusalem**, then:

```powershell
powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1
```

This registers a 10:00 AM daily task. Logs go to `daily_summary/logs/` if something fails.

---

## Manual runs

Override the weekday router when you need a specific date:

```bash
# Force daily for a specific date
python daily_summary/generate_morning_elite.py --force daily --date 2026-07-07

# Force weekend (default: last Thu–Sat)
python daily_summary/generate_morning_elite.py --force weekend

# Weekend with explicit dates
python daily_summary/generate_weekend_summary.py --dates 2026-07-09,2026-07-10,2026-07-11
```

---

## Report layout (baselines)

Use these as the format reference — don't change layout without diffing against them.

| Report | Baseline date | Reference file |
|--------|---------------|----------------|
| **Daily** | 2026-07-07 | `daily_summary/daily_summaries/2026-07-07_elite_daily_summary_canvas.html` |
| **Weekend** | 2026-07-12 lock | `daily_summary/daily_summaries/2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html` |

Each daily report includes:

1. **{Weekday} vs last {weekday}** — Jackpota + Elite WoW
2. **Top 20 Same Day Comparison** — purchases, hold, urgency, reason, recommendation
3. Per-player handoffs (see `wow-drop-reason-analysis` skill for deep dives)

---

## Folder guide

```
daily_summary/          Daily/weekend implementation, scheduler, HTML export, outputs
wow_drop_analysis/      Same-weekday reason logic, exports, and player handoffs
feedback_cro/           Feedback analysis generator, docs, and exports
decline_protocol/       Rolling 7-day decline cohort protocol
elite_reference/        Enterprise SQL and source reference files
Elite.MD                Terminology and KPI rules (read before reporting)
.cursor/skills/         Cursor agent skills (@daily-elite-summary)
```

---

## In Cursor

Type `@daily-elite-summary` or say **"run morning elite"** to generate the report from chat.

---

## Troubleshooting

| Problem | What to check |
|---------|----------------|
| `git` / `python` not found | Restart terminal after install; confirm PATH |
| BigQuery auth error | `GOOGLE_APPLICATION_CREDENTIALS` or default key path |
| Scheduled task ran but no file | Latest log in `daily_summary/logs/morning_elite_*.log` |
| Wrong report type | Use `--force daily` or `--force weekend` |

---

## GitHub Pages

Published reports are copied to `docs/` after each HTML export.

**Enable once** in the repo on GitHub:

1. **Settings** → **Pages**
2. **Build and deployment** → Source: **Deploy from a branch**
3. Branch: **main** (or your default), folder: **/docs**
4. Save

Site URL (org repo):

`https://silver-social-games.github.io/EliteDailySummary-/`

- **Home:** `docs/index.html` — latest Daily/Weekend + archive
- **Latest:** `docs/latest.html` (Daily/Weekend only)
- **Archive:** `docs/reports/` — `*_elite_daily_summary_canvas.html` and weekend canvases

AM Brief is local review only (`am_daily_dashboard/exports/` + canvas). It is **not** published to GitHub Pages.

After a local Daily/Weekend run, HTML is copied into `docs/`.

**Scheduled GitHub Pages auto-publish is currently disabled.** The implementation
is retained in `daily_summary/publish_pages_git.py`, but the registered scheduled
task does not opt in to commit or push. See
`daily_summary/github-pages-auto-publish-spec.md` and
`daily_summary/github-pages-auto-publish-review.md` before enabling it.

Manual publish (if needed):

```bash
python daily_summary/publish_pages_git.py --dry-run
python daily_summary/publish_pages_git.py
```

Safety: only `docs/latest.html`, `docs/index.html`, `docs/reports.json`, and
`docs/reports/*.html`; no force push; no empty commits.

Tests:

```bash
python -m unittest daily_summary.test_publish_pages_git -v
```
---

- **Workflow:** [`daily_summary/DAILY_SUMMARY.md`](daily_summary/DAILY_SUMMARY.md)
- **Definitions & rules:** [`Elite.MD`](Elite.MD)
- **Agent setup:** [`AGENTS.md`](AGENTS.md)
