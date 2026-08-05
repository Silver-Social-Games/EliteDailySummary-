---
name: purchase-lookup
description: Generates Elite order-level purchase history with offer codes, GC/SC, free spins, and timestamps. Use when the user asks what an AID purchased, requests offer codes or order details, or needs an Elite purchase export.
---

# Elite Purchase Lookup

**Canonical workflow:** [`purchase_lookup/PURCHASE_LOOKUP.md`](../../../purchase_lookup/PURCHASE_LOOKUP.md)

**Definitions:** [`Elite.MD`](../../../Elite.MD) — **Terminology**, **Rewards and
promotions**, **Account status and decline reasons**.

## When to use

- Check **what a player purchased** (offer codes, USD, GC, SC, free spins)
- Open an Elite date range and type an AID into the canvas search bar
- Find the **leading offer** for a player or date range
- Elite book-wide purchase list (by date range / agent)
- Share CSV or HTML with agents

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"

# Single player (default: last 30 days)
python purchase_lookup/generate_purchase_lookup.py --aid 458523630

# Custom date range
python purchase_lookup/generate_purchase_lookup.py --aid 458523630 --from 2026-06-01 --to 2026-06-30

# Elite managed book (max 7 days without explicit --from)
python purchase_lookup/generate_purchase_lookup.py --elite --from 2026-06-26 --to 2026-07-02
python purchase_lookup/generate_purchase_lookup.py --elite --agent rachel_a --from 2026-06-26 --to 2026-07-02

# Layout dry run
python purchase_lookup/generate_purchase_lookup.py --no-query
```

**Cursor:** `@purchase-lookup` or "run purchase lookup for AID …"

The Elite-wide 7-day default limits scan cost and output size. Do not loosen it;
require an explicit `--from` date for longer ranges.

In Elite-wide mode, use the canvas **Find purchases by AID** search bar to filter all tables and totals to one player.

## Outputs

| Artifact | Path |
|----------|------|
| Live canvas | `~/.cursor/projects/<workspace>/canvases/purchase-lookup[-{AID}].canvas.tsx` |
| Canvas backup | `purchase_lookup/handoffs/purchase-lookup[-{AID}].canvas.tsx` |
| JSON snapshot | `purchase_lookup/handoffs/YYYY-MM-DD_{slug}_purchase_lookup.json` |
| HTML export | `purchase_lookup/exports/purchase-lookup-{slug}-{date}.html` |
| CSV export | `purchase_lookup/exports/purchase-lookup-{slug}-{date}.csv` |

## Terminology

- **AID** — always show `account_id` as AID
- **Orders** = Purchases (`payment_payment_orders`, succeeded, not refunded)
- **Offer code** — `payment_offer_templates.code`
- **SC / GC** — `sc_amount` / `gc_amount` on the order
- **Free spins** — attributed from `fact_rewards` by same day + campaign code match (see `PURCHASE_LOOKUP.md`)

## Credentials

Follow `.cursor/rules/bigquery-analytics.mdc`. Never print or copy credential contents.

**Note:** `fact_rewards` exceeds MCP scan cap — run via Python generator, not MCP.
