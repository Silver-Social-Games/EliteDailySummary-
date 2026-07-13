# Elite Daily Summary

Elite morning reports for the managed book — same-weekday Jackpota + Elite compare, Top 20 Same Day Comparison, canvas + HTML export.

**Canonical definitions:** [`Elite.MD`](Elite.MD) · **Workflow:** [`daily_summary/DAILY_SUMMARY.md`](daily_summary/DAILY_SUMMARY.md)

---

## Schedule (Sun–Thu, 10:00 Israel)

| Generation day | Report |
|----------------|--------|
| **Sunday** | Prior Thu + Fri + Sat (weekend bundle) |
| **Mon–Thu** | Yesterday (daily) |
| **Fri/Sat** | Skip |

```bash
python daily_summary/generate_morning_elite.py
```

Register Windows task (once):

```powershell
powershell -ExecutionPolicy Bypass -File daily_summary\register_daily_summary_task.ps1
```

---

## Setup

```bash
pip install -r requirements.txt
```

**Credentials:** set `GOOGLE_APPLICATION_CREDENTIALS` to your BigQuery service account JSON, or place `key.json.json` at the default path documented in `Elite.MD`.

**Warehouse:** `silver-social-games-data` (EU)

---

## Output

| Artifact | Path |
|----------|------|
| Markdown | `daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary.md` |
| HTML | `daily_summary/daily_summaries/*_canvas.html` |
| Canvas | `~/.cursor/projects/<workspace>/canvases/elite-daily-summary-*.canvas.tsx` |

### Format baselines

| Report | Baseline |
|--------|----------|
| Daily | **2026-07-07** |
| Weekend | **2026-07-12** format lock (`2026-07-09` to `2026-07-11` data) |

---

## Layout

```
daily_summary/     # Entry scripts, scheduler, HTML export
decline_check/     # BigQuery, reason logic, canvas generators (core dependency)
Elite.MD           # Terminology and KPI rules
```

**Cursor skill:** `.cursor/skills/daily-elite-summary/` — use `@daily-elite-summary` in chat.
