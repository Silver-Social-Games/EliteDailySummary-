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
```

Default report date = **yesterday**. Outputs are **local only** (canvas +
`am_daily_dashboard/exports/`). Do **not** publish AM Brief to GitHub Pages.

Standalone HTML refresh from existing JSON:

```bash
python am_daily_dashboard/canvas_to_html.py am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json
```

**In Cursor:** `@elite-am-brief` or "run AM Brief" / "morning AM board".

## Output

| Artifact | Path |
|----------|------|
| Canvas | `canvases/elite-am-brief-YYYY-MM-DD.canvas.tsx` |
| HTML | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.html` |
| JSON | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json` |

After running, open the dated canvas beside chat and/or the HTML export.

## Locked product decisions

- Title **Elite AM Brief**; subtitle date only (`{Weekday} {DD Mon YYYY}`)
- Top purchasers: **Purchases (#)** + Top Offer (no Qty / Offer $)
- **Pending RD** ≥ $5k created in last **3 days**
- **Locks** = still locked **and** `DATE(locked_at) = report_date` (any lock reason)
- **Open Tickets** — TID links to Zendesk
- **Top 20** via `fetch_top_same_day_by_agent` (same selection/classify as Elite Daily Decline; up to 20 per AM)
- HTML via `canvas_to_html` interactive shell (Overview + AM tabs) — **not** a static table dump
- **Not** on GitHub Pages — Daily/Weekend publish to `docs/`; AM Brief stays local

## Sections (see canonical doc)

Overview + per-AM tabs: Empowering intro, Elite & Jackpota + AM share, Morning Checklist, Top 10 Purchasers, Top 20 · WoW Purchase Gaps, Pending Redemptions, First-Time Locked RD, Birthdays · Last 3 Days, Open Tickets, Locked And Take A Break.

## Terminology

Apply `.cursor/rules/elite-core.mdc` and `.cursor/rules/bigquery-analytics.mdc`.
Use **Elite**, **AID**, **Purchased players**. TID = Zendesk ticket ID.

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.
