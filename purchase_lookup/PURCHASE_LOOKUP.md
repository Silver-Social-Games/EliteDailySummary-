# Elite Purchase Lookup

Order-level purchase history for Elite players — offer codes, GC/SC, free spins, timestamps.

**Canonical reference:** [`Elite.MD`](../Elite.MD) — **Terminology**, **Rewards
and promotions**, **Account status and decline reasons**. **Generator:**
`generate_purchase_lookup.py`

---

## When to use

- Check **what a player purchased** (offer codes, amounts, GC/SC, free spins)
- Open an Elite date range and use the **AID search bar** to find one player instantly
- Find the **leading offer** for a player or date range
- Share purchase detail with agents (CSV / HTML export)
- Reopen the interactive canvas anytime in Cursor

**Not for:** headline Elite revenue (use daily summary + KPI `purchased`). This tool reads **orders** from `payment_payment_orders`.

---

## Terminology

| Term | Rule |
|------|------|
| **AID** | `account_id` — always show as **AID** |
| **Orders** | = **Purchases** — `payment_payment_orders` where `status = 'succeeded'` and `refunded = false` |
| **Offer code** | `payment_offer_templates.code` via `offer_id` |
| **SC** | `sc_amount` on the order (total SC credited, purchase + bonus) |
| **SC bonus** | `GREATEST(sc_amount - amount, 0)` |
| **GC** | `gc_amount` on the order |
| **Free spins** | From `fact_rewards` — attributed to orders by same calendar day + campaign code match (see below) |
| **Agent** | `tag_agent_1` from `dbt_utils.elite_account_tags` (latest snapshot) |

---

## Run

```bash
cd "c:\Users\Owner\Downloads\Elite"

# Single player (default window: last 30 days)
python purchase_lookup/generate_purchase_lookup.py --aid 458523630

# Custom date range
python purchase_lookup/generate_purchase_lookup.py --aid 458523630 --from 2026-06-01 --to 2026-06-30

# Elite managed book (requires --from; max 7 days default)
python purchase_lookup/generate_purchase_lookup.py --elite --from 2026-06-26 --to 2026-07-02
python purchase_lookup/generate_purchase_lookup.py --elite --agent rachel_a --from 2026-06-26 --to 2026-07-02

# Layout dry run (no BigQuery)
python purchase_lookup/generate_purchase_lookup.py --no-query
```

**Cursor:** `@purchase-lookup` or "run purchase lookup for AID …"

**Search bar workflow:** run an Elite range, open the canvas, then type an AID (for example `458523630`) into **Find purchases by AID**. The totals, leading offer, offer-code summary, order table, and unlinked free spins narrow to that AID.

**Credentials:** `GOOGLE_APPLICATION_CREDENTIALS` or default `c:\Users\Owner\Downloads\key.json.json`

---

## Outputs

| Artifact | Path |
|----------|------|
| Live canvas | `~/.cursor/projects/<workspace>/canvases/purchase-lookup[-{AID}].canvas.tsx` |
| Canvas backup | `purchase_lookup/handoffs/purchase-lookup[-{AID}].canvas.tsx` |
| JSON snapshot | `purchase_lookup/handoffs/YYYY-MM-DD_{AID}_purchase_lookup.json` |
| HTML export | `purchase_lookup/exports/purchase-lookup-{slug}-{date}.html` |
| CSV export | `purchase_lookup/exports/purchase-lookup-{slug}-{date}.csv` |

---

## Data sources

| Field | Table / column |
|-------|----------------|
| Orders | `transactional_data.payment_payment_orders` |
| Offer code / title | `transactional_data.payment_offer_templates` |
| Name | `uam_accounts` + `uam_persons` |
| Agent | `dbt_utils.elite_account_tags` (latest snapshot) |
| Free spins | `jackpota_agg.fact_rewards` (`product_title = 'freespin'`) |
| Elite book filter | `dbt_aninditac.elite` + `elite_account_tags` (`tag_agent_1 IS NOT NULL`) |

---

## Free spins attribution

There is **no foreign key** from orders to free spins. Attribution rules:

1. Same `account_id`
2. `campaign_code` contains the order `offer_code` (or base offer without trailing `_NN`)
3. Date match: `reward_date` = purchase date **or** campaign embeds purchase day (`YYYYMMDD_...`) **or** reward posts within 5 days after purchase

**FS count** per order: summed `total_spins` (fallback `reward_count`) from matched freespin campaigns.

**Unlinked FS:** freespin campaigns that did not match any order offer code — shown separately (aggregated by campaign, not per spin row).

**MCP note:** `fact_rewards` exceeds the 1 GB MCP cap — always run this generator via Python + service account.

---

## Account check

When interpreting $0 purchase days, always check `uam_accounts.locked` and `lock_reason` before outreach (see `Elite.MD` **Account status and decline reasons**).

---

## Out of scope (v1)

- Failed purchase attempts (`status = 'created'`)
- KPI vs orders reconciliation chart
- Scheduled / automated runs
