# Elite Negative Feedback — CRO Canvas

Negative Elite player feedback joined to BigQuery purchased and NGR.
**Definitions:** [`Elite.MD`](../Elite.MD) — **Terminology** (NGR) and
**Revenue and Purchased players**.

**Cursor skill:** `@elite-feedback-cro`

---

## Source file

Default Excel input:

`c:\Users\Owner\OneDrive - Silver Social Games\Desktop\VIP\Cursor\Elite Feedback.xlsx`

Override:

```bash
python feedback_cro/generate_elite_feedback_cro_canvas.py --xlsx "path/to/Elite Feedback.xlsx"
```

---

## Run (one command — canvas + exports)

```bash
cd "c:\Users\Owner\Downloads\Elite"
python feedback_cro/generate_elite_feedback_cro_canvas.py --copy-desktop
```

| Flag | Purpose |
|------|---------|
| `--xlsx PATH` | Custom feedback Excel file |
| `--copy-desktop` | Also copy HTML + MD to `Desktop\VIP\Cursor\` |
| `--no-query` | Skip BigQuery (dry run / layout test) |
| `--before-start`, `--before-end` | Override the default baseline window |
| `--after-start`, `--after-end` | Override the comparison window; end defaults to today |

Pin all four dates when reproducing or sharing a historical report.

---

## Outputs

| Artifact | Path |
|----------|------|
| **Live canvas** | `C:\Users\Owner\.cursor\projects\c-Users-Owner-Downloads-Elite\canvases\elite-feedback-cro.canvas.tsx` |
| Canvas backup | `feedback_cro/handoffs/elite-feedback-cro.canvas.tsx` |
| **HTML export** (matches canvas) | `feedback_cro/exports/elite-feedback-cro-export.html` |
| Markdown export | `feedback_cro/exports/elite-feedback-cro-export.md` |
| Desktop copy | `Desktop\VIP\Cursor\Elite-Feedback-CRO-Export.html` |
| Generator | `feedback_cro/generate_elite_feedback_cro_canvas.py` |

---

## Open the canvas in Cursor

1. `Ctrl + P`
2. Paste the live canvas path above
3. Click **Open Canvas** on the editor tab

---

## HTML export = same design as canvas

The HTML file is **interactive** (works in any browser):

- Dark theme, stats, bar chart, filterable pie with tag labels + %
- Click pie slice / legend / pill to filter players
- Search box + tag dropdown
- Full table + expandable feedback per player

Double-click `Elite-Feedback-CRO-Export.html` on Desktop to open.

---

## Counts

| Term | Meaning |
|------|---------|
| **Total feedback entries** | Rows with feedback text in Excel |
| **Negative players** | Unique AIDs with at least one negative theme after merge |
| **Excluded** | Empty or purely positive unique players |
| **Tag mentions** | Pie total; one player can appear in multiple themes |

**Default windows:** Before 22 Apr – 18 May · After 19 May – 15 Jun (edit dates in `generate_elite_feedback_cro_canvas.py` if needed)

---

## Tag buckets

| Tag | Label |
|-----|-------|
| `no_wins` | No Wins / Dry Play |
| `rewards` | Rewards & Bonuses |
| `competitors` | Playing Elsewhere |
| `support` | Support / Live Agent |
| `redemption` | Redemption / Payout |
| `product_ux` | Product / UX |
| `churn` | Churn / Break |

---

## Metrics

Per player from `jackpota_agg.daily_player_revenue_kpis`:

- **Lifetime purchased** — all time
- **Purchased / NGR** — equal before/after windows
- **Purchase change / NGR change** — after minus before

Negative-only filter: exclude purely positive entries; mixed feedback keeps full verbatim text.
