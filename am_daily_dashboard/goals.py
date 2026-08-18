"""Elite AM Brief — Goals targets, weights, run-rate, and weighted tracking.

Targets: versioned TSV at am_daily_dashboard/data/elite_goals.tsv
Weights: locked Q3 board weights (sum 80%; remaining 20% out of scope).
"""

from __future__ import annotations

import calendar
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_GOALS_TSV = DATA_DIR / "elite_goals.tsv"

# Locked KPI weights (screenshot). Sum = 80%. Do not invent the remaining 20%.
KPI_WEIGHTS: dict[str, float] = {
    "daily_avg_purchase": 15.0,
    "daily_avg_net_purchase": 15.0,
    "monthly_purchasers": 15.0,
    "arppu": 15.0,
    "reactivations": 8.0,
    "upgrades": 5.0,
    "pct_active": 7.0,
}
INCLUDED_WEIGHT_TOTAL = sum(KPI_WEIGHTS.values())  # 80.0

KPI_ORDER = [
    "daily_avg_purchase",
    "daily_avg_net_purchase",
    "monthly_purchasers",
    "arppu",
    "reactivations",
    "upgrades",
    "pct_active",
]

KPI_LABELS: dict[str, str] = {
    "daily_avg_purchase": "Daily Avg Purchase",
    "daily_avg_net_purchase": "Daily Avg Net Purchase",
    "monthly_purchasers": "Monthly Purchasers",
    "arppu": "ARPPU",
    "reactivations": "# Reactivation",
    "upgrades": "Upgrade to Elite",
    "pct_active": "% Active from portfolio",
}

# How each KPI's month-end pace is projected. Measured on Jun/Jul 2026:
#   revenue accrues linearly (day-16 share 0.51-0.55 vs 16/31 = 0.516) and so
#   do reactivations (0.535/0.580), but distinct monthly purchasers (0.89-0.94)
#   and upgrades (0.86-0.90) saturate. Extrapolating those linearly projected
#   Coral to 914 purchasers out of a 621-player portfolio, so they use an
#   empirical month-shape divisor instead. ARPPU and % Active are derived from
#   the paced components rather than paced on their own.
#   % Active is point-in-time (share of the book whose last purchase is inside
#   the inactivity window), so like a daily average it is already a month-end
#   rate and is not projected.
PACE_IS_ACTUAL = frozenset(
    {"daily_avg_purchase", "daily_avg_net_purchase", "pct_active"}
)
PACE_RUN_RATE = frozenset({"reactivations"})
PACE_BY_SHAPE = {"monthly_purchasers": "purchasers", "upgrades": "upgrades"}
PACE_DERIVED = frozenset({"arppu"})

# Sanity band for a shape divisor before we trust it.
SHAPE_MIN = 0.05
SHAPE_MAX = 1.0

GOALS_AGENT_TAGS = ("coral_s", "gabriel_e", "lee_t", "rachel_a")
GOALS_AGENT_DISPLAY = {
    "coral_s": "Coral",
    "gabriel_e": "Gabriel",
    "lee_t": "Lee",
    "rachel_a": "Rachel",
}

# Achievement capped at 100% of goal (same as goals_q2 achievement_ratio).
ACHIEVEMENT_CAP = 1.0


@dataclass(frozen=True)
class GoalsTarget:
    agent: str
    year: int
    month: int
    quarter: int
    daily_avg_purchase: float
    daily_avg_net_purchase: float
    monthly_purchasers: float
    reactivations: float
    upgrades: float
    pct_active: float  # stored as percent points, e.g. 96.0 for 96%
    arppu: float | None  # None when blank (Q2 rows)


def parse_number(raw: object) -> float | None:
    """Parse TSV cells with commas, percentages, blanks → float or None."""
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "").replace('"', "").replace("%", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_number_required(raw: object, default: float = 0.0) -> float:
    v = parse_number(raw)
    return default if v is None else v


def achievement_ratio(actual: float, goal: float) -> float:
    """Partial credit up to ACHIEVEMENT_CAP (1.0), matching goals_q2."""
    if goal <= 0:
        return ACHIEVEMENT_CAP if actual >= 0 else 0.0
    return min(ACHIEVEMENT_CAP, actual / goal)


def month_bounds(report_date: date) -> tuple[date, int, int]:
    """Return (month_start, elapsed_days inclusive, days_in_month)."""
    month_start = report_date.replace(day=1)
    elapsed = (report_date - month_start).days + 1
    days_in_month = calendar.monthrange(report_date.year, report_date.month)[1]
    return month_start, elapsed, days_in_month


def load_goals_tsv(path: Path | None = None) -> list[GoalsTarget]:
    path = path or DEFAULT_GOALS_TSV
    rows: list[GoalsTarget] = []
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = path.open(newline="", encoding="utf-16")
    else:
        text = path.open(newline="", encoding="utf-8-sig")
    with text as f:
        sample = f.read(4096)
        f.seek(0)
        delim = "\t" if "\t" in sample.splitlines()[0] else ","
        reader = csv.DictReader(f, delimiter=delim)
        for rec in reader:
            agent = (rec.get("Agent Name") or "").strip()
            if not agent or agent.lower() in {"total", ""}:
                continue
            if agent not in GOALS_AGENT_TAGS:
                continue
            month = int(parse_number_required(rec.get("month")))
            year = int(parse_number_required(rec.get("year")))
            quarter = int(parse_number_required(rec.get("Q")))
            if month < 1 or year < 2000:
                continue
            rows.append(
                GoalsTarget(
                    agent=agent,
                    year=year,
                    month=month,
                    quarter=quarter,
                    daily_avg_purchase=parse_number_required(
                        rec.get("Daily Avg Purchase")
                    ),
                    daily_avg_net_purchase=parse_number_required(
                        rec.get("Daily Avg Net Purchase")
                    ),
                    monthly_purchasers=parse_number_required(
                        rec.get("Monthly Players w purchase")
                    ),
                    reactivations=parse_number_required(rec.get("#Reactivations")),
                    upgrades=parse_number_required(
                        rec.get("#Players Upgraded to Elite")
                    ),
                    pct_active=parse_number_required(
                        rec.get("% Active From Portfolio")
                    ),
                    arppu=parse_number(rec.get("ARPPU (avg purchase per paying player)")),
                )
            )
    return rows


def targets_for_month(
    report_date: date, path: Path | None = None
) -> dict[str, GoalsTarget]:
    """Map agent tag → GoalsTarget for report_date's calendar month."""
    all_rows = load_goals_tsv(path)
    out: dict[str, GoalsTarget] = {}
    for row in all_rows:
        if row.year == report_date.year and row.month == report_date.month:
            out[row.agent] = row
    return out


def run_rate_pace(mtd: float, elapsed_days: int, days_in_month: int) -> float:
    if elapsed_days <= 0:
        return 0.0
    return (mtd / elapsed_days) * days_in_month


def clean_shape(raw: object) -> float | None:
    """Accept a month-shape divisor only inside the sanity band."""
    value = parse_number(raw)
    if value is None:
        return None
    if not (SHAPE_MIN <= value <= SHAPE_MAX):
        return None
    return value


def shape_pace(mtd: float, shape: float | None, cap: float | None = None) -> float | None:
    """Project month-end for a saturating KPI: MTD / share-of-month-reached.

    Never below MTD (already banked) and never above `cap` (e.g. portfolio
    size, which distinct purchasers cannot exceed).
    """
    if shape is None:
        return None
    projected = max(mtd, mtd / shape)
    if cap is not None and cap > 0:
        projected = min(projected, cap)
    return projected


def _status_for(measure: float, goal: float) -> str:
    if goal <= 0:
        return "n/a"
    ratio = measure / goal
    if ratio >= 1.0:
        return "On track"
    if ratio >= 0.9:
        return "Close"
    return "Behind"


def _fmt_money(n: float) -> str:
    return f"${n:,.0f}"


def _fmt_num(n: float, decimals: int = 0) -> str:
    if decimals == 0:
        return f"{n:,.0f}"
    return f"{n:,.{decimals}f}"


def _fmt_pct_points(n: float) -> str:
    return f"{n:.1f}%"


def build_agent_goals_block(
    agent_tag: str,
    target: GoalsTarget | None,
    actuals: dict[str, Any],
    report_date: date,
    *,
    upgrades_available: bool = True,
    upgrades_note: str = "",
) -> dict[str, Any] | None:
    """Build the Goals payload section for one AM. None if Alon / no targets."""
    if agent_tag not in GOALS_AGENT_TAGS:
        return None
    if target is None:
        return {
            "agent": agent_tag,
            "agentName": GOALS_AGENT_DISPLAY[agent_tag],
            "available": False,
            "note": f"No goals TSV row for {report_date.strftime('%b %Y')}.",
            "kpis": [],
            "weightedTrackedPct": None,
            "includedWeightTotal": INCLUDED_WEIGHT_TOTAL,
            "elapsedDays": None,
            "daysInMonth": None,
            "upgradesNote": upgrades_note,
        }

    month_start, elapsed, days_in_month = month_bounds(report_date)
    mtd_purchase = float(actuals.get("mtd_purchase") or 0)
    mtd_net = float(actuals.get("mtd_net_purchase") or 0)
    mtd_net_paid_redeem = float(actuals.get("mtd_net_purchase_paid_redeem") or 0)
    purchasers = float(actuals.get("monthly_purchasers") or 0)
    reactivations = float(actuals.get("reactivations") or 0)
    upgrades = actuals.get("upgrades")
    # Unlocked accounts only — the book an AM can actually work.
    portfolio = float(actuals.get("portfolio_size") or 0)
    portfolio_all = float(actuals.get("portfolio_size_all") or 0)
    portfolio_locked = float(actuals.get("portfolio_locked") or 0)

    daily_avg_purchase = mtd_purchase / elapsed if elapsed else 0.0
    daily_avg_net = mtd_net / elapsed if elapsed else 0.0
    arppu_actual = (mtd_purchase / purchasers) if purchasers > 0 else 0.0
    # Active players are counted point-in-time (last purchase inside the
    # inactivity window), not "bought at some point this month" — that is what
    # the AMs' Tableau report measures.
    active_players = float(actuals.get("active_players") or 0)
    pct_active_actual = (
        min(100.0, active_players / portfolio * 100.0) if portfolio > 0 else 0.0
    )

    raw_values = {
        "daily_avg_purchase": daily_avg_purchase,
        "daily_avg_net_purchase": daily_avg_net,
        "monthly_purchasers": purchasers,
        "arppu": arppu_actual,
        "reactivations": reactivations,
        "upgrades": float(upgrades) if upgrades is not None else None,
        "pct_active": pct_active_actual,
    }

    purchasers_shape = clean_shape(actuals.get("purchasers_shape"))
    upgrades_shape = clean_shape(actuals.get("upgrades_shape"))
    paced_purchasers = shape_pace(
        purchasers, purchasers_shape, cap=portfolio or None
    )
    paced_month_purchase = daily_avg_purchase * days_in_month
    paced_values: dict[str, float | None] = {
        "daily_avg_purchase": daily_avg_purchase,
        "daily_avg_net_purchase": daily_avg_net,
        "monthly_purchasers": paced_purchasers,
        "reactivations": run_rate_pace(reactivations, elapsed, days_in_month),
        "upgrades": (
            shape_pace(float(upgrades), upgrades_shape)
            if upgrades is not None
            else None
        ),
        # ARPPU and % Active only make sense against paced purchasers: at day
        # 16 the month's spend is half in but almost all purchasers are known,
        # so MTD ARPPU reads ~55% of month-end and looks falsely Behind.
            "arppu": (
                paced_month_purchase / paced_purchasers
                if paced_purchasers and paced_purchasers > 0
                else None
            ),
            "pct_active": pct_active_actual,
        }
    shape_note = {
        "monthly_purchasers": purchasers_shape,
        "upgrades": upgrades_shape,
    }
    goals_map = {
        "daily_avg_purchase": target.daily_avg_purchase,
        "daily_avg_net_purchase": target.daily_avg_net_purchase,
        "monthly_purchasers": target.monthly_purchasers,
        "arppu": target.arppu,
        "reactivations": target.reactivations,
        "upgrades": target.upgrades,
        "pct_active": target.pct_active,
    }

    kpis: list[dict[str, Any]] = []
    weighted_points = 0.0
    weight_used = 0.0

    for key in KPI_ORDER:
        label = KPI_LABELS[key]
        weight = KPI_WEIGHTS[key]
        goal = goals_map[key]
        actual = raw_values[key]

        if key == "upgrades" and not upgrades_available:
            kpis.append(
                {
                    "key": key,
                    "label": label,
                    "weight": weight,
                    "weightLabel": f"{weight:g}%",
                    "goal": goal,
                    "goalDisplay": _fmt_num(goal) if goal is not None else "—",
                    "actual": None,
                    "actualDisplay": "—",
                    "pace": None,
                    "paceDisplay": "—",
                    "gap": None,
                    "gapDisplay": "—",
                    "status": "Unavailable",
                    "statusTone": "neutral",
                    "achievement": None,
                    "paceBasis": "",
                    "note": upgrades_note
                    or "Upgrade actual source not available for this month.",
                }
            )
            continue

        if goal is None:
            kpis.append(
                {
                    "key": key,
                    "label": label,
                    "weight": weight,
                    "weightLabel": f"{weight:g}%",
                    "goal": None,
                    "goalDisplay": "—",
                    "actual": actual,
                    "actualDisplay": _display_kpi(key, actual),
                    "pace": None,
                    "paceDisplay": "—",
                    "gap": None,
                    "gapDisplay": "—",
                    "status": "No goal",
                    "statusTone": "neutral",
                    "achievement": None,
                    "paceBasis": "",
                    "note": "Goal blank in TSV (e.g. Q2 ARPPU).",
                }
            )
            continue

        assert actual is not None
        pace = paced_values.get(key)
        # No trustworthy projection: judge on what is banked so far.
        measure_for_status = pace if pace is not None else actual

        gap = goal - measure_for_status
        ach = achievement_ratio(measure_for_status, goal)
        weighted_points += ach * weight
        weight_used += weight
        status = _status_for(measure_for_status, goal)
        tone = (
            "success"
            if status == "On track"
            else ("warning" if status == "Close" else "danger")
        )

        kpis.append(
            {
                "key": key,
                "label": label,
                "weight": weight,
                "weightLabel": f"{weight:g}%",
                "goal": goal,
                "goalDisplay": _display_kpi(key, goal),
                "actual": actual,
                "actualDisplay": _display_kpi(key, actual),
                "pace": pace,
                "paceDisplay": _display_kpi(key, pace) if pace is not None else "—",
                "gap": gap,
                "gapDisplay": _display_gap(key, gap),
                "status": status,
                "statusTone": tone,
                "achievement": round(ach * 100.0, 2),
                "paceBasis": _pace_basis(key, pace, shape_note.get(key)),
                "note": "",
            }
        )

    tracked_pct = (
        (weighted_points / weight_used * 100.0) if weight_used > 0 else None
    )

    return {
        "agent": agent_tag,
        "agentName": GOALS_AGENT_DISPLAY[agent_tag],
        "available": True,
        "monthLabel": report_date.strftime("%b %Y"),
        "monthStart": month_start.isoformat(),
        "asOf": report_date.isoformat(),
        "elapsedDays": elapsed,
        "daysInMonth": days_in_month,
        "portfolioSize": int(portfolio),
        "portfolioSizeAll": int(portfolio_all),
        "portfolioLocked": int(portfolio_locked),
        "mtdPurchase": mtd_purchase,
        "mtdNetPurchase": mtd_net,
        "mtdNetPurchasePaidRedeem": mtd_net_paid_redeem,
        "dailyNetPaidRedeem": (
            mtd_net_paid_redeem / elapsed if elapsed else 0.0
        ),
        "kpis": kpis,
        "weightedTrackedPct": round(tracked_pct, 1) if tracked_pct is not None else None,
        "weightedTrackedDisplay": (
            f"{tracked_pct:.1f}% of included {weight_used:g}% weight"
            if tracked_pct is not None
            else "—"
        ),
        "includedWeightTotal": INCLUDED_WEIGHT_TOTAL,
        "weightUsed": weight_used,
        "achievementCapNote": (
            "Achievement per KPI capped at 100% of goal "
            "(same as goals_q2 achievement_ratio); overperformance does not "
            "add extra points. Score is % of included weight only — not a "
            "100% corporate score (manager 20% out of scope)."
        ),
        "upgradesNote": upgrades_note,
        "purchasersShape": purchasers_shape,
        "upgradesShape": upgrades_shape,
        # Which tag snapshot the book resolved to. Should equal asOf; if it does
        # not, the roster drifted and any mismatch against the AM's own table is
        # explained by that before any definition is questioned.
        "bookSnapshotDate": (
            str(actuals.get("book_snapshot_date"))
            if actuals.get("book_snapshot_date")
            else ""
        ),
        "definitionsNote": (
            "MTD Actual columns are month-to-date through the as-of date. "
            "Daily avgs = MTD / elapsed days. "
            "Net Purchase = by requested redeem: purchased − (requested redeem "
            "− cancelled) − chargeback − refunds, after account/date agg. "
            "Reactivation and % Active match the AMs' Tableau report: "
            "purchases from successful payment orders; Reactivation = purchase "
            "after a gap of ≥20 days (Tableau churn_period_days), once per AID "
            "in the month; % Active = players whose last purchase is within 30 "
            "days of the as-of date, over the whole tagged book — locked accounts "
            "are counted on both sides, because a tagged player contributes to "
            "every KPI regardless of lock status. "
            "Pace projects month-end: daily avgs and % Active are already a "
            "month-end rate; Reactivations extrapolate linearly; Monthly "
            "Purchasers and Upgrades divide by the share of the month reached "
            "by this day in the two prior months, because both saturate rather "
            "than accrue linearly; ARPPU is rebuilt from the paced numbers. "
            "Status compares Pace (not Actual) to goal."
        ),
    }


def _pace_basis(key: str, pace: float | None, shape: float | None) -> str:
    """One-line explanation of how this KPI's pace was projected."""
    if pace is None:
        return "No month-end projection — Status reads MTD actual vs goal."
    if key == "pct_active":
        return (
            "Point-in-time: share of the whole tagged book whose last purchase "
            "is within 30 days, so it is already a month-end rate."
        )
    if key in PACE_IS_ACTUAL:
        return "Daily average is already month-end pace (spend accrues linearly)."
    if key in PACE_RUN_RATE:
        return "MTD / elapsed days x days in month (accrues linearly)."
    if key in PACE_BY_SHAPE:
        share = f"{shape * 100:.0f}%" if shape else "n/a"
        return (
            f"MTD / {share} — share of the month already reached by this day "
            "in the two prior months (this KPI saturates, so linear "
            "extrapolation over-projects)."
        )
    if key == "arppu":
        return "Paced monthly purchase / paced monthly purchasers."
    return ""


def _display_kpi(key: str, value: float | None) -> str:
    if value is None:
        return "—"
    if key in {"daily_avg_purchase", "daily_avg_net_purchase", "arppu"}:
        return _fmt_money(value)
    if key == "pct_active":
        return _fmt_pct_points(value)
    return _fmt_num(value)


def _display_gap(key: str, gap: float) -> str:
    """Gap = goal − measure; positive means still short of goal."""
    if key in {"daily_avg_purchase", "daily_avg_net_purchase", "arppu"}:
        sign = "-" if gap < 0 else ""
        return f"{sign}${abs(gap):,.0f}"
    if key == "pct_active":
        return f"{gap:+.1f}pp"
    return f"{gap:+,.0f}"


def actuals_by_agent(rows: list[dict]) -> dict[str, dict]:
    """Index BigQuery goals_mtd_actuals rows by agent tag (normalize gabriel)."""
    out: dict[str, dict] = {}
    for r in rows:
        tag = str(r.get("agent") or "").strip()
        if tag == "gabriel":
            tag = "gabriel_e"
        if tag not in GOALS_AGENT_TAGS:
            continue
        out[tag] = r
    return out


def strip_payload_for_am(payload: dict, agent_name: str) -> dict:
    """File-level isolation: one AM's sections only — no Overview, no other AMs."""
    agents = [a for a in payload.get("agents") or [] if a.get("agentName") == agent_name]
    if not agents:
        raise ValueError(f"No agent block for {agent_name}")
    report = dict(payload.get("report") or {})
    report["title"] = f"Elite AM Brief · {agent_name}"
    report["overviewGreetingLines"] = []
    # goalsAmOrder names every AM on the board, so narrow it too — an AM's own
    # file should not even carry the roster of who else is measured.
    goals_meta = dict(payload.get("goalsMeta") or {})
    if goals_meta.get("goalsAmOrder"):
        goals_meta["goalsAmOrder"] = [agent_name]
    # Drop multi-AM overview / share tables entirely.
    return {
        "report": report,
        "amShares": [],
        "overview": [],
        "agents": agents,
        "amOrder": [agent_name],
        "goalsMeta": goals_meta,
        "singleAm": True,
        "singleAmName": agent_name,
    }
