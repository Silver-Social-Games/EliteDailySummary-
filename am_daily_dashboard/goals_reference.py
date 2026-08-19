"""The AM's own Goals figures, so the audit diffs itself instead of by hand.

Reconciling Aug 2026 took several rounds of the AM reading numbers off their table
while the board's numbers were read off the console. That loop found two real bugs
(the unpinned book, the % Active denominator), but it is slow and it is the reason
a 32-account roster leak survived for two days.

Paste the AM's table into data/elite_goals_reference.tsv once per as-of date and
`--goals-only` prints a Yours and Gap column beside every KPI, so a drift is
visible in the same six seconds it takes to run the audit.

Columns match elite_goals.tsv exactly except for `day`, so a row can be copied
across with the headers unchanged. `day` is the as-of day of month and must match
the report date — a reference captured on the 16th says nothing about the 17th.
Blank cells simply do not diff.

A `team` row is accepted too, and diffs against the manager's own Team Goals view.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from goals import DATA_DIR, GOALS_TARGET_TAGS, parse_number

DEFAULT_REFERENCE_TSV = DATA_DIR / "elite_goals_reference.tsv"

# Audit KPI label -> (reference TSV column, unit). Labels are the ones the audit
# already prints, so the diff lines up without a second naming scheme. The unit is
# explicit rather than sniffed from the label: "Monthly Purchasers" contains the
# substring "Purchase" and was formatted as dollars when it was inferred.
KPI_SPECS: dict[str, tuple[str, str]] = {
    "Daily Avg Purchase": ("Daily Avg Purchase", "usd"),
    "Daily Avg Net Purchase": ("Daily Avg Net Purchase", "usd"),
    "Monthly Purchasers": ("Monthly Players w purchase", "count"),
    "ARPPU": ("ARPPU (avg purchase per paying player)", "usd"),
    "# Reactivation": ("#Reactivations", "count"),
    "Upgrade to Elite": ("#Players Upgraded to Elite", "count"),
    "% Active from portfolio": ("% Active From Portfolio", "pct"),
}


@dataclass(frozen=True)
class ReferenceRow:
    agent: str
    year: int
    month: int
    day: int
    values: dict[str, float]


def _int_cell(raw: object) -> int:
    v = parse_number(raw)
    return 0 if v is None else int(v)


def load_reference_tsv(path: Path | None = None) -> list[ReferenceRow]:
    """Load the AM-supplied figures. Missing file is normal — returns []."""
    path = path or DEFAULT_REFERENCE_TSV
    if not path.exists():
        return []
    rows: list[ReferenceRow] = []
    raw = path.read_bytes()
    encoding = (
        "utf-16"
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff")
        else "utf-8-sig"
    )
    with path.open(newline="", encoding=encoding) as handle:
        for rec in csv.DictReader(handle, delimiter="\t"):
            agent = (rec.get("Agent Name") or "").strip()
            # `team` is accepted alongside the four AMs so the manager can paste
            # their own sheet and have the audit diff the team row too — that
            # gap otherwise has to be decomposed by hand, which is exactly what
            # cost time when Alon turned out to be missing from the rollup.
            if agent not in GOALS_TARGET_TAGS:
                continue
            year, month, day = (
                _int_cell(rec.get("year")),
                _int_cell(rec.get("month")),
                _int_cell(rec.get("day")),
            )
            if year < 2000 or not 1 <= month <= 12 or not 1 <= day <= 31:
                continue
            values = {}
            for label, (column, _unit) in KPI_SPECS.items():
                v = parse_number(rec.get(column))
                if v is not None:
                    values[label] = v
            if values:
                rows.append(ReferenceRow(agent, year, month, day, values))
    return rows


def reference_for(
    rows: list[ReferenceRow], agent_tag: str, as_of: str
) -> dict[str, float]:
    """Figures for one agent on one as-of date (ISO). Empty when absent."""
    try:
        year, month, day = (int(p) for p in as_of.split("-"))
    except (ValueError, AttributeError):
        return {}
    for r in rows:
        if (r.agent, r.year, r.month, r.day) == (agent_tag, year, month, day):
            return r.values
    return {}


def gap_text(label: str, actual: float | None, theirs: float | None) -> tuple[str, str]:
    """Return (theirs, gap) display strings for one audit row.

    Percentages diff in points; everything else in absolute units with a percent
    of their figure, since a $700 gap means something different on $24,000 than on
    a count of 8.
    """
    if theirs is None:
        return "", ""
    unit = KPI_SPECS.get(label, ("", "count"))[1]
    is_pct = unit == "pct"
    theirs_display = (
        f"{theirs:.1f}%" if is_pct
        else f"${theirs:,.0f}" if unit == "usd"
        else f"{theirs:,.0f}"
    )
    if actual is None:
        return theirs_display, ""
    diff = actual - theirs
    if is_pct:
        gap = "match" if abs(diff) < 0.05 else f"{diff:+.1f}pp"
        return theirs_display, gap
    if abs(diff) < 0.5:
        return theirs_display, "match"
    pct = f" ({diff / theirs * 100:+.1f}%)" if theirs else ""
    return theirs_display, f"{diff:+,.0f}{pct}"
