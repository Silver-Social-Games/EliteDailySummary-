# Daily Summary

Elite morning report — same-weekday Jackpota + Elite compare, Top 20 Same Day Comparison, canvas.

**Definitions:** [`Elite.MD`](../Elite.MD) — **Terminology**, **Elite managed
book**, **Revenue and Purchased players**, **Account status and decline
reasons**. **Reason logic:** `wow_drop_analysis/wow_drop_reason.py`

---

## Schedule (Sun–Thu)

| Generation day | Script path | Report date(s) |
|----------------|-------------|----------------|
| **Sunday** | weekend | Prior **Thu, Fri, Sat** |
| **Monday** | daily | Yesterday = **Sunday** |
| **Tuesday** | daily | Monday |
| **Wednesday** | daily | Tuesday |
| **Thursday** | daily | Wednesday |
| **Friday / Saturday** | *(skip)* | Thu–Sat covered on Sunday |

Thursday report day is only in the **weekend bundle**, not a standalone daily.

---

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python daily_summary/generate_morning_elite.py
```

Manual override:

```bash
python daily_summary/generate_morning_elite.py --force weekend
python daily_summary/generate_morning_elite.py --force daily --date 2026-07-07
python daily_summary/generate_daily_summary.py --date YYYY-MM-DD
python daily_summary/generate_weekend_summary.py --dates 2026-07-09,2026-07-10,2026-07-11
```

**AM Brief board** (per-AM Top 10, decline, RD, birthdays, ZD, locks):

```bash
python am_daily_dashboard/generate_am_daily_dashboard.py
python am_daily_dashboard/generate_am_daily_dashboard.py --date YYYY-MM-DD
```

See [`am_daily_dashboard/AM_DAILY_DASHBOARD.md`](../am_daily_dashboard/AM_DAILY_DASHBOARD.md).

**Schedule:** daily **10:00 Israel time** — register once:

```powershell
powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1
```

Windows uses the **local clock**; set system timezone to **(UTC+02:00) Jerusalem** (or run the task at the equivalent local hour).

**Cursor:** `@daily-elite-summary` or “run morning elite”.

**GitHub Pages auto-publish is currently disabled.** The registered scheduled
task generates the report but does not opt in to commit or push. The retained
implementation is documented in
[`github-pages-auto-publish-spec.md`](github-pages-auto-publish-spec.md).
Dry-run: `python daily_summary/publish_pages_git.py --dry-run`.
Tests: `python -m unittest daily_summary.test_publish_pages_git -v`.

### Format baselines (locked)

| Report | Baseline | Reference artifact |
|--------|----------|-------------------|
| **Daily** | **2026-07-07** (Tue) | `daily_summaries/2026-07-07_elite_daily_summary_canvas.html` |
| **Weekend** | **2026-07-12** format lock | `daily_summaries/2026-07-09_to_2026-07-11_elite_weekend_summary_canvas.html` |

Daily: H1 only, segment 8-col table, Top 20 + filters + Zendesk modal (14 player columns).
Weekend: 3 segment tables at top, Top 20 below, day pills + Select, 60-player filter bar — no `Weekend · WoW` H2.

The HTML files are durable layout references. Regenerate `.canvas.tsx` artifacts
when an interactive comparison is needed.

### View in Chrome (matches Cursor canvas)

Auto-exported when you run the daily summary:

```bash
python daily_summary/generate_daily_summary.py
start daily_summary\daily_summaries\2026-07-01_elite_daily_summary_canvas.html
```

Or export manually from the canvas file:

```bash
python daily_summary/canvas_to_html.py --date YYYY-MM-DD
```

---

## Output

| Artifact | Path |
|----------|------|
| Markdown | `daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary.md` |
| HTML (Chrome, canvas design) | `daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary_canvas.html` — auto on each run |
| Weekend HTML | `daily_summary/daily_summaries/YYYY-MM-DD_to_YYYY-MM-DD_elite_weekend_summary_canvas.html` |
| Canvas (daily) | `~/.cursor/projects/<workspace>/canvases/elite-daily-summary-YYYY-MM-DD.canvas.tsx` |
| Canvas (weekend) | `~/.cursor/projects/<workspace>/canvases/elite-weekend-summary-YYYY-MM-DD_to_YYYY-MM-DD.canvas.tsx` |
| Stakeholder canvas | `~/.cursor/projects/<workspace>/canvases/elite-stakeholder-summary-YYYY-MM-DD.canvas.tsx` |

---

## Report sections

1. **{Weekday} vs last {weekday} · Elite & Jackpota** — platform + Elite WoW
2. **Top 20 Same Day Comparison** — LT Purchase, Lifetime Hold, urgency, Reason, Recommendation
3. **Per-player handoffs** — `@wow-drop-reason-analysis`

---

## Credentials

`GOOGLE_APPLICATION_CREDENTIALS` or `c:\Users\Owner\Downloads\key.json.json`

---

## Shared implementation

`daily_summary/generate_daily_elite_summary.py` remains the shared runtime module
for report logic. It is not the scheduled entry point. Use
`daily_summary/generate_morning_elite.py` for new runs.
