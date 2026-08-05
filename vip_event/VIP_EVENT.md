# VIP Event — Top 50 (Excel + presentation)

Vegas VIP event materials for the **Top 50 Elite** invite list.
**Definitions:** [`Elite.MD`](../Elite.MD) — **Elite managed book**,
**Terminology** (Seniority, Net Purchase, Hold), **Player value segment**.

The event roster is supplied by the source workbook. It intentionally does not
rebuild the canonical `dbt_aninditac.elite` book; reconcile differences only
when dashboard parity is requested.

**Top 30** brief is separate — see `generate_vegas_top30_elite_brief.py` (not part of Top 50 workflow).

**Folder:** `vip_event/`

---

## Top 50 — player roster tab

Source workbook (OneDrive):

`Desktop\VIP\VIP Event\VIP Event - Top 50 Players .xlsx`

| Script | Purpose |
|--------|---------|
| `enrich_top50_xlsx.py` | Refresh NP 30d/60d on roster tab |
| `generate_top50_management_brief.py` | Presentation + Top 50 Brief tabs |
| `apply_top50_swaps.py` | Apply roster swaps + regenerate brief |

**Other agent / manual:** own tab `VIP Event - Top 50 Players ` only — do not edit Schedule or Focus Points.

```bash
python vip_event/enrich_top50_xlsx.py
python vip_event/generate_top50_management_brief.py
```

```bash
python vip_event/generate_top50_management_pptx.py
```

| Input | `Desktop\VIP\VIP Event\VIP-Event-Top50-Management.xlsx` |
| Output | `Desktop\VIP\VIP Event\VIP Event - Vegas 2026.pptx` (backup + prepend 3 slides) |

Close Excel and PowerPoint before running.

---

## Top 50 — Schedule & Focus Points

Adds **Schedule** and **Focus Points** tabs to the same workbook and writes matching PowerPoint slides.

**This agent owns:** `Schedule`, `Focus Points` tabs + `VIP Event - Vegas 2026 - updated.pptx`  
**Does not touch:** roster tab, Top 30 files.

```bash
cd "c:\Users\Owner\Downloads\Elite"
python vip_event/generate_top50_event_tabs.py
python vip_event/generate_top50_event_tabs.py --source "path\to\VIP Event - Top 50 Players .xlsx"
python vip_event/generate_top50_event_tabs.py --pptx "path\to\VIP Event - Vegas 2026.pptx"
```

| Output | Path |
|--------|------|
| Workbook (in-place tabs) | OneDrive `VIP Event - Top 50 Players .xlsx` |
| Export copy | `vip_event/exports/VIP Event - Top 50 Players - schedule-focus.xlsx` |
| PowerPoint | `vip_event/exports/VIP Event - Vegas 2026 - updated.pptx` |

Close the xlsx in Excel before running (OneDrive lock).

---

## Top 30 (separate cohort)

```bash
python vip_event/generate_vegas_top30_elite_brief.py --copy-desktop
```

See exports under `vip_event/exports/vegas-vip-event-elite-top30.*`.
