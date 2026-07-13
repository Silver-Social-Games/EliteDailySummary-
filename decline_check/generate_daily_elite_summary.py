"""
Daily Elite summary — BigQuery report for managed Elite book.
Run from project root:
  python decline_check/generate_daily_elite_summary.py

Output: decline_check/daily_summaries/YYYY-MM-DD_elite_daily_summary.md

Requires: google-cloud-bigquery, pandas (optional for tables)
Credentials: GOOGLE_APPLICATION_CREDENTIALS or default key path below.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "daily_summaries"
DEFAULT_KEY = Path(r"c:\Users\Owner\Downloads\key.json.json")
PROJECT_ID = "silver-social-games-data"
# S-Jackpota Account Portal (Looker dashboard 5207). Override via LOOKER_ACCOUNT_PORTAL_URL.
DEFAULT_LOOKER_ACCOUNT_PORTAL_URL = (
    "https://lookerpatrianna.cloud.looker.com/dashboards/5207?Account+ID+={aid}"
)
DEFAULT_ZENDESK_AGENT_BASE = "https://jackpotahelp.zendesk.com"


def looker_account_portal_url(aid: object) -> str:
    """Looker Jackpota Account Portal for an AID. Template uses {aid} or {account_id}."""
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    template = os.environ.get("LOOKER_ACCOUNT_PORTAL_URL", DEFAULT_LOOKER_ACCOUNT_PORTAL_URL)
    return template.format(aid=aid_s, account_id=aid_s)


def format_aid_markdown(aid: object) -> str:
    aid_s = str(aid or "").strip()
    if not aid_s:
        return ""
    url = looker_account_portal_url(aid_s)
    return f"[{aid_s}]({url})" if url else aid_s


def zendesk_new_ticket_url(requester_id: object = None) -> str:
    """Zendesk Agent Workspace new ticket. Pre-selects requester when id is known."""
    base = os.environ.get("ZENDESK_AGENT_BASE_URL", DEFAULT_ZENDESK_AGENT_BASE).rstrip("/")
    url = f"{base}/agent/tickets/new/1"
    rid = str(requester_id or "").strip()
    if rid and rid.isdigit():
        return f"{url}?requester_id={rid}"
    return url


def format_ticket_markdown(draft: dict) -> str:
    if not draft.get("ticketEnabled"):
        return "—"
    url = draft.get("zendeskUrl") or ""
    subject = (draft.get("ticketSubject") or "").replace("|", "/")
    preview = subject if len(subject) <= 48 else subject[:47].rstrip() + "…"
    if url:
        return f"[Draft]({url}) · _{preview}_"
    return f"_{preview}_"


def get_client() -> bigquery.Client:
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", str(DEFAULT_KEY))
    if Path(key_path).exists():
        creds = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds, location="EU")
    return bigquery.Client(project=PROJECT_ID, location="EU")


def run_query(client: bigquery.Client, sql: str) -> list[dict]:
    rows = client.query(sql).result()
    return [dict(r.items()) for r in rows]


def weekday_label(d: date) -> str:
    return d.strftime("%A")


def top10_table_titles(day_name: str) -> dict[str, str]:
    """Column and section titles - each word capitalized."""
    return {
        "this_purchase": f"This {day_name} Purchase",
        "prior_purchase": f"Prior {day_name} Purchase",
        "purchase_7d": "7D Purchase",
        "lifetime_purchase": "LT Purchase",
        "lifetime_hold": "Lifetime Hold",
        "favourite_game_7d": "Favourite Game (7D)",
        "urgency": "Urgency",
        "reason": "Reason",
        "recommendation": "Recommendation",
        "ticket": "Ticket",
        "agent_name": "Agent Name",
        "aid": "AID",
        "name": "Name",
        "delta": "Delta",  # internal sort key only; not shown in table
    }


def build_sql(report_date: date) -> dict[str, str]:
    rd = report_date.isoformat()
    # Same weekday compare: report date vs 7 days earlier (e.g. Tuesday vs Tuesday)
    this_day = report_date.isoformat()
    prior_day = (report_date - timedelta(days=7)).isoformat()
    w0_start = (report_date - timedelta(days=6)).isoformat()
    w1_start = (report_date - timedelta(days=13)).isoformat()
    w1_end = (report_date - timedelta(days=7)).isoformat()
    gp_start = (report_date - timedelta(days=6)).isoformat()

    base_cte = f"""
    WITH latest AS (
      SELECT MAX(snapshot_date) AS snap
      FROM `{PROJECT_ID}.dbt_utils.elite_account_tags`
    ),
    elite AS (
      -- Tableau "Yesterday Performance" book: dbt_aninditac.elite (Elite tag + Zendesk-managed)
      SELECT DISTINCT
        e.account_id AS AID,
        COALESCE(t.tag_agent_1, e.agent_name) AS agent
      FROM `{PROJECT_ID}.dbt_aninditac.elite` e
      CROSS JOIN latest l
      LEFT JOIN `{PROJECT_ID}.dbt_utils.elite_account_tags` t
        ON e.account_id = t.account_id
        AND t.snapshot_date = l.snap
        AND t.category = 'Elite'
        AND t.tag_agent_1 IS NOT NULL
    ),
    purchases AS (
      SELECT account_id AS AID, date,
        SUM(CAST(purchased AS FLOAT64)) AS bought,
        SUM(CAST(profit AS FLOAT64) - CAST(loss AS FLOAT64)) AS ngr,
        SUM(COALESCE(sc_reward_amount, 0) + COALESCE(sc_envelopes_amount, 0)) AS bonus_sc
      FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
      WHERE date BETWEEN DATE '{w1_start}' AND DATE '{rd}'
      GROUP BY 1, 2
    ),
    player AS (
      SELECT e.AID, e.agent,
        SUM(IF(p.date BETWEEN DATE '{w0_start}' AND DATE '{rd}', p.bought, 0)) AS w0,
        SUM(IF(p.date BETWEEN DATE '{w1_start}' AND DATE '{w1_end}', p.bought, 0)) AS w1,
        SUM(IF(p.date BETWEEN DATE '{w0_start}' AND DATE '{rd}', p.ngr, 0)) AS ngr_7d,
        SUM(IF(p.date BETWEEN DATE '{w0_start}' AND DATE '{rd}', p.bonus_sc, 0)) AS bonus_7d,
        MAX(IF(p.date = DATE '{this_day}', p.bought, 0)) AS day_this,
        MAX(IF(p.date = DATE '{prior_day}', p.bought, 0)) AS day_prior_week
      FROM elite e
      LEFT JOIN purchases p ON e.AID = p.AID
      GROUP BY 1, 2
    ),
    active_decliners AS (
      SELECT * FROM player
      WHERE w0 > 0 AND w1 > 0 AND w0 < w1
    )
    """

    return {
        "weekday_compare": f"""
        {base_cte},
        day_cmp AS (
          SELECT p.date,
            ROUND(SUM(p.bought), 2) AS revenue,
            COUNT(DISTINCT CASE WHEN p.bought > 0 THEN p.AID END) AS players
          FROM purchases p
          INNER JOIN elite e ON p.AID = e.AID
          WHERE p.date IN (DATE '{this_day}', DATE '{prior_day}')
          GROUP BY 1
        )
        SELECT * FROM day_cmp ORDER BY date DESC
        """,
        "overall_weekday_compare": f"""
        WITH day_kpi AS (
          SELECT
            account_id,
            date,
            SUM(CAST(purchased AS FLOAT64)) AS purchased
          FROM `{PROJECT_ID}.jackpota_agg.daily_player_revenue_kpis`
          WHERE date IN (DATE '{this_day}', DATE '{prior_day}')
          GROUP BY 1, 2
        )
        SELECT
          date,
          ROUND(SUM(purchased), 2) AS revenue,
          COUNT(DISTINCT CASE WHEN purchased > 0 THEN account_id END) AS players
        FROM day_kpi
        GROUP BY 1
        ORDER BY date DESC
        """,
        "reasons": f"""
        {base_cte},
        pending_redeem AS (
          SELECT account_id, amount,
            ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY created_at DESC) AS rn
          FROM `{PROJECT_ID}.transactional_data.payment_withdraw_money_requests`
          WHERE status IN ('pre_authorized', 'locked')
        ),
        tagged AS (
          SELECT ad.*, eu.redeem_status, eu.locked, eu.red_flag,
            ROUND(ad.w1 - ad.w0, 2) AS wow_drop,
            CASE
              WHEN COALESCE(pd.amount, 0) > 0
                THEN 'redemption_in_progress'
              WHEN ad.ngr_7d >= 5000 THEN 'big_win_last_7d'
              WHEN ad.ngr_7d <= -5000 THEN 'big_loss_last_7d'
              WHEN ad.day_this = 0 AND ad.day_prior_week > 0 THEN 'same_weekday_skip'
              WHEN eu.locked THEN 'account_locked'
              WHEN eu.red_flag = 1 THEN 'red_flag'
              ELSE 'general_spend_softening'
            END AS primary_reason
          FROM active_decliners ad
          LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
            ON ad.AID = eu.account_id AND eu.report_date = DATE '{rd}'
          LEFT JOIN pending_redeem pd
            ON ad.AID = pd.account_id AND pd.rn = 1
        )
        SELECT primary_reason, COUNT(*) AS players, ROUND(SUM(wow_drop), 2) AS revenue_drop,
          ROUND(AVG(ngr_7d), 2) AS avg_ngr_7d, ROUND(AVG(bonus_7d), 2) AS avg_bonus_7d
        FROM tagged GROUP BY 1 ORDER BY revenue_drop DESC
        """,
        "top_decliners": f"""
        {base_cte}
        SELECT ad.AID, ad.agent, eu.name,
          ROUND(ad.w1, 2) AS prior_week_bought,
          ROUND(ad.w0, 2) AS this_week_bought,
          ROUND(ad.w1 - ad.w0, 2) AS wow_drop,
          ROUND(ad.ngr_7d, 2) AS ngr_7d,
          ROUND(ad.bonus_7d, 2) AS bonus_7d,
          eu.preferred_game_last_30_days AS favourite_game_30d,
          eu.redeem_status AS redemption_workflow_status
        FROM active_decliners ad
        LEFT JOIN `{PROJECT_ID}.dbt_dashboards_mart.elite_users` eu
          ON ad.AID = eu.account_id AND eu.report_date = DATE '{rd}'
        ORDER BY wow_drop DESC LIMIT 15
        """,
        "agents": f"""
        {base_cte}
        SELECT agent, COUNT(*) AS active_decliners, ROUND(SUM(w1 - w0), 2) AS revenue_drop
        FROM active_decliners GROUP BY 1 ORDER BY revenue_drop DESC
        """,
        "games": f"""
        {base_cte},
        ad AS (SELECT AID FROM active_decliners),
        gameplay AS (
          SELECT g.account_id AS AID, g.product_title, SUM(g.nrows) AS spins
          FROM `{PROJECT_ID}.jackpota_agg.fact_gameplay_daily` g
          INNER JOIN ad ON g.account_id = ad.AID
          WHERE DATE(g.at) BETWEEN DATE '{gp_start}' AND DATE '{rd}'
            AND g.product_title IS NOT NULL AND g.product_title != 'Jackpot'
          GROUP BY 1, 2
        ),
        ranked AS (
          SELECT AID, product_title,
            ROW_NUMBER() OVER (PARTITION BY AID ORDER BY spins DESC) AS rn
          FROM gameplay
        )
        SELECT product_title AS favourite_game_7d, COUNT(*) AS active_decliners
        FROM ranked WHERE rn = 1
        GROUP BY 1 ORDER BY active_decliners DESC LIMIT 10
        """,
    }


def fmt_money(v) -> str:
    if v is None:
        return "-"
    return f"${round(float(v)):,}"


REASON_LABELS = {
    "redemption_in_progress": "Redemption in progress",
    "big_win_last_7d": "Big win (7d)",
    "big_loss_last_7d": "Big loss (7d)",
    "same_weekday_skip": "Same weekday skip",
    "account_locked": "Account locked",
    "red_flag": "Red flag",
    "general_spend_softening": "General spend softening",
}


def fmt_reason(code: str) -> str:
    return REASON_LABELS.get(code, code.replace("_", " "))


def _day_row(rows: list[dict], d: date) -> dict:
    return next((r for r in rows if str(r.get("date"))[:10] == d.isoformat()), {})


def _wow_marker(chg: float) -> str:
    if chg > 0:
        return "🟢 "
    if chg < 0:
        return "🔴 "
    return ""


def _fmt_rev_wow(this: float, prior: float) -> str:
    chg = this - prior
    pct = (chg / prior * 100) if prior else 0
    return f"{_wow_marker(chg)}{fmt_money(chg)} ({pct:+.1f}%)"


def _fmt_ply_wow(this: int, prior: int) -> str:
    chg = this - prior
    pct = (chg / prior * 100) if prior else 0
    return f"{_wow_marker(chg)}{chg:+d} ({pct:+.1f}%)"


def _segment_wow_row(
    label: str,
    row_this: dict,
    row_prior: dict,
    *,
    share: str = "",
) -> str:
    rev_this = float(row_this.get("revenue") or 0)
    ply_this = int(row_this.get("players") or 0)
    rev_prior = float(row_prior.get("revenue") or 0)
    ply_prior = int(row_prior.get("players") or 0)
    return (
        f"| **{label}** | {fmt_money(rev_this)} | {fmt_money(rev_prior)} | "
        f"{_fmt_rev_wow(rev_this, rev_prior)} | {ply_this} | {ply_prior} | "
        f"{_fmt_ply_wow(ply_this, ply_prior)} | {share or ''} |"
    )


def _summary_headline(
    day_name: str,
    overall_this: dict,
    overall_prior: dict,
    elite_this: dict,
    elite_prior: dict,
    elite_share: float,
) -> str:
    rev_o = float(overall_this.get("revenue") or 0)
    rev_op = float(overall_prior.get("revenue") or 0)
    rev_e = float(elite_this.get("revenue") or 0)
    rev_ep = float(elite_prior.get("revenue") or 0)
    pct_o = ((rev_o - rev_op) / rev_op * 100) if rev_op else 0
    pct_e = ((rev_e - rev_ep) / rev_ep * 100) if rev_ep else 0
    return (
        f"**Headline:** Jackpota revenue {pct_o:+.1f}% vs last {day_name} · "
        f"Elite revenue {pct_e:+.1f}% vs last {day_name} · "
        f"Elite share {elite_share:.1f}% of Jackpota"
    )


def _combined_wow_table(
    day_name: str,
    overall_this: dict,
    overall_prior: dict,
    elite_this: dict,
    elite_prior: dict,
    elite_share: float,
) -> list[str]:
    return [
        f"| Segment | This {day_name} Purchase | Prior {day_name} Purchase | Purchase WoW | "
        f"This {day_name} Purchased Players | Prior {day_name} Purchased Players | Purchased Players WoW | Share |",
        "|---------|--------------------:|---------------------:|------------:|"
        "-------------------------------:|--------------------------------:|----------------------:|------:|",
        _segment_wow_row("Jackpota", overall_this, overall_prior),
        _segment_wow_row(
            "Elite",
            elite_this,
            elite_prior,
            share=f"{elite_share:.1f}% of Jackpota",
        ),
    ]


def render_markdown(
    report_date: date,
    day_rows: list[dict],
    overall_rows: list[dict],
    top10_delta: list[dict],
) -> str:
    prior_day = report_date - timedelta(days=7)
    day_name = weekday_label(report_date)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    elite_this = _day_row(day_rows, report_date)
    overall_this = _day_row(overall_rows, report_date)
    elite_prior = _day_row(day_rows, prior_day)
    overall_prior = _day_row(overall_rows, prior_day)
    elite_rev = float(elite_this.get("revenue") or 0)
    overall_rev = float(overall_this.get("revenue") or 0)
    elite_share = (elite_rev / overall_rev * 100) if overall_rev else 0

    from wow_drop_reason import (
        M_NONE_IN_7D,
        fmt_money,
        format_action_markdown,
        format_agent_name,
        format_purchase_7d_help,
        format_reason_markdown,
        format_table_lifetime_hold,
        format_table_lifetime_purchase,
        format_table_money,
        format_table_purchase_7d,
        format_table_urgency,
        format_urgency_legend,
    )

    lines = [
        f"# Elite Daily Decline Dashboard · {report_date.isoformat()}",
        "",
        f"**Generated:** {generated}  ",
        f"**Report date:** {report_date.isoformat()} ({day_name})  ",
        f"**Compare:** this {day_name} {report_date.isoformat()} vs prior {day_name} {prior_day.isoformat()}",
        "",
        "Definitions: **Jackpota** = all platform players (Overall) · **Elite** = `dbt_aninditac.elite` · "
        "**Purchase** = KPI `purchased` · "
        "**Purchased players** = distinct with purchased > 0 that day (after account-level KPI agg) · "
        "**Compare** = report day vs prior same weekday.",
        "",
        f"## {day_name} vs last {day_name} · Elite & Jackpota",
        "",
        *_combined_wow_table(
            day_name,
            overall_this,
            overall_prior,
            elite_this,
            elite_prior,
            elite_share,
        ),
        "",
        _summary_headline(
            day_name, overall_this, overall_prior, elite_this, elite_prior, elite_share
        ),
        "",
        "## Top 20 · WoW Purchase Gaps",
        "",
        f"_Sorted: **Urgency** (Today → 48h → Watch) then prior-weekday purchase gap desc. "
        f"Prioritize **$0 report-day purchase** until majority of Elite WoW drop is covered. "
        f"This {day_name} {report_date.isoformat()} vs prior {day_name} {prior_day.isoformat()}. "
        f"{format_purchase_7d_help()}_",
        "",
    ]

    lines.append(format_urgency_legend())
    titles = top10_table_titles(day_name)
    lines.extend([
        "",
        f"| # | {titles['agent_name']} | {titles['aid']} | {titles['name']} | {titles['lifetime_purchase']} | {titles['lifetime_hold']} | {titles['this_purchase']} | {titles['prior_purchase']} | {titles['purchase_7d']} | {titles['favourite_game_7d']} | {titles['urgency']} | {titles['reason']} | {titles['recommendation']} | {titles['ticket']} |",
        f"|---|----------|------|------|----------------:|------:|----------:|-----------:|--------------|---------------------:|---------|--------|----------------|--------|",
    ])

    def _md_cell(text: str) -> str:
        return (text or "").replace("|", "/")

    prior_total = 0.0
    for i, row in enumerate(top10_delta, 1):
        name = row.get("name") or "n/a"
        p7d = row.get("purchase_7d_combined", row.get("purchase_calendar", M_NONE_IN_7D))
        prior_total += float(row.get("prior_weekday") or 0)
        lines.append(
            f"| {i} | {_md_cell(format_agent_name(row))} | {format_aid_markdown(row.get('AID', ''))} | {_md_cell(name)} | "
            f"{_md_cell(format_table_lifetime_purchase(row.get('lifetime_purchased')))} | "
            f"{_md_cell(format_table_lifetime_hold(row.get('lifetime_hold_pct', 'n/a')))} | "
            f"{_md_cell(format_table_money(row.get('this_weekday'), emphasize_zero=True))} | "
            f"{_md_cell(format_table_money(row.get('prior_weekday'), emphasize_high=True))} | "
            f"{_md_cell(format_table_purchase_7d(p7d))} | "
            f"{_md_cell(row.get('favourite_game_7d', '—'))} | "
            f"{_md_cell(format_table_urgency(row.get('urgency', '')))} | "
            f"{_md_cell(format_reason_markdown(row.get('reason_table', row.get('reason_detail', ''))))} | "
            f"{_md_cell(format_action_markdown(row.get('recommendation', row.get('action', ''))))} | "
            f"{_md_cell(format_ticket_markdown(row))} |"
        )

    if top10_delta:
        lines.append(
            f"| | | | **Total ({len(top10_delta)})** | | | | **{fmt_money(prior_total)}** | | | | | | |"
        )

    lines.extend([
        "",
        "_**Reason** = compact case tags joined by ● (restriction, Zendesk missing doc from ticket "
        "**description**, last purchase, activity). Sources: `uam_accounts`, `elite_users`, "
        "`daily_player_revenue_kpis`, `fact_gameplay_daily`, `payment_payment_orders`, "
        "`payment_withdraw_money_requests`, `zendesk.ticket` (subjects Last 14D; POA/KYC "
        "description Last 30D; POA resolution from `zendesk.ticket_comment`)._",
        "",
        "_**Inactive / suspicious / skip-day** — if offline, restricted, redeem-stuck, **same-weekday skip**, "
        "or Reason incomplete: check Zendesk ticket **description + tags** (not subjects alone) before "
        "purchase push — skip may be POA/KYC/suspend block. Example: POA declined → valid utility bill "
        "still awaited. Escalate Compliance/Ops with the specific item; no purchase ask until cleared._",
        "",
        "_**LT Purchase** = all-time KPI `purchased` (account-level, rounded). "
        "**Lifetime Hold** = lifetime net purchase ÷ lifetime purchased._",
        "",
        "_**Favourite Game (7D)** = highest spin volume in Rolling 7D Window (`fact_gameplay_daily`, excl. Jackpot)._",
        "",
        "_**Played Today · No Purchase** = spun/bet on report day but $0 purchased that day — confirm "
        "rhythm skip in Zendesk if redeem workflow or restriction tickets exist._",
        "",
        "_**Ticket** = Zendesk draft link (subject preview). Full editable email drafts in HTML/canvas export — "
        "copy message then open Zendesk (requester pre-selected when known)._",
        "",
        "## Per-Player Handoffs",
        "",
        "Deep dive and agent canvas: `@wow-drop-reason-analysis`",
        "",
        "```bash",
        f"python decline_check/wow_drop_player_handoff.py --aid AID --date {report_date.isoformat()}",
        "```",
        "",
        "Rolling 7d decline cohort: `python decline_check/generate_decline_protocol.py`",
        "",
        "*Source: `silver-social-games-data` · See `Elite.MD`*",
    ])

    return "\n".join(lines) + "\n"


def resolve_report_date(arg_date: str | None) -> date:
    """Default: yesterday. Use --date YYYY-MM-DD to pin (e.g. Tuesday run)."""
    if arg_date:
        return date.fromisoformat(arg_date)
    return date.today() - timedelta(days=1)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Elite daily summary")
    parser.add_argument(
        "--date",
        dest="report_date",
        help="Report date (YYYY-MM-DD), e.g. 2026-06-02 for Tuesday",
    )
    args = parser.parse_args()
    report_date = resolve_report_date(args.report_date)
    client = get_client()
    sql = build_sql(report_date)

    print(f"Running Elite daily summary for {report_date} ({weekday_label(report_date)})...")
    from wow_drop_reason import fetch_top10_by_delta

    day_rows = run_query(client, sql["weekday_compare"])
    overall_rows = run_query(client, sql["overall_weekday_compare"])
    prior_day = report_date - timedelta(days=7)
    elite_this = _day_row(day_rows, report_date)
    elite_prior = _day_row(day_rows, prior_day)
    elite_wow_drop = max(
        0.0,
        float(elite_prior.get("revenue") or 0) - float(elite_this.get("revenue") or 0),
    )
    top10_delta = fetch_top10_by_delta(client, report_date, elite_wow_drop=elite_wow_drop)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{report_date.isoformat()}_elite_daily_summary.md"
    content = render_markdown(report_date, day_rows, overall_rows, top10_delta)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote {out_path}")

    from generate_daily_elite_canvas import write_daily_canvas, write_stakeholder_canvas

    canvas_path = write_daily_canvas(report_date, day_rows, overall_rows, top10_delta)
    print(f"Wrote {canvas_path}")

    try:
        import sys

        ds = PROJECT_ROOT / "daily_summary"
        if str(ds) not in sys.path:
            sys.path.insert(0, str(ds))
        from canvas_to_html import export_for_canvas

        export_for_canvas(canvas_path)
    except Exception as exc:
        print(f"HTML canvas export skipped: {exc}")

    stakeholder_path = write_stakeholder_canvas(report_date, day_rows, overall_rows)
    print(f"Wrote {stakeholder_path}")


if __name__ == "__main__":
    main()
