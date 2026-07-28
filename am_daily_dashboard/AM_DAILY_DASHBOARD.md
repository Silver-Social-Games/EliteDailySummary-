# Elite AM Brief

Morning board for Coral, Gabriel, Lee, Rachel, and Alon — complementary to the Elite Daily Decline Top 20.

**Definitions:** [`Elite.MD`](../Elite.MD) · **Decline reasons:** `decline_check/wow_drop_reason.py`

---

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"
python am_daily_dashboard/generate_am_daily_dashboard.py
python am_daily_dashboard/generate_am_daily_dashboard.py --date 2026-07-27
```

Default report date = **yesterday**.

---

## Output

| Artifact | Path |
|----------|------|
| Canvas | `~/.cursor/projects/.../canvases/elite-am-brief-YYYY-MM-DD.canvas.tsx` |
| HTML | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.html` — canvas-matched interactive export (Overview + AM tabs), same pattern as Daily Summary |
| JSON | `am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json` |

HTML is built by injecting the JSON payload into `handoffs/elite_am_brief_web.html` via `canvas_to_html.write_am_brief_html` (not a static table dump).

Standalone refresh from existing JSON:

```bash
python am_daily_dashboard/canvas_to_html.py am_daily_dashboard/exports/YYYY-MM-DD_elite_am_brief.json
```

---

## Sections

### Overview
1. Greeting (once)
2. **Elite & Jackpota** weekday summary + **AM Share Of Elite** (incl. Purchased / Book)
3. AM Overview metrics (click AM pill → that AM tab only)

### Per AM tab
1. Empowering intro with AM share of Elite + purchased players out of book
2. **Elite & Jackpota** weekday summary (same as Overview)
3. **Morning Checklist** (metric labels jump to sections)
4. **Top 10 Purchasers** — Purchases (#) + Top Offer (no Qty / Offer $)
5. **Top 20 · WoW Purchase Gaps** — Daily Elite selection/classify logic, up to 20 per AM
6. **Pending Redemptions** — locked RD ≥ $5,000 created in last **3 days**
7. **First-Time Locked RD** — section always shown (empty when none)
8. **Birthdays · Last 3 Days** — DOB as D/M/Y + Age
9. **Open Tickets** — LTP, Hold, 7D Purchase + Ticket TIDs link to Zendesk
10. **Locked And Take A Break** — still locked **and** `DATE(locked_at) = report_date` (past day), **any** lock reason

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