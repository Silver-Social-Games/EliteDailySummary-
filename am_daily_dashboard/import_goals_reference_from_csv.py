"""Import Tableau Goals w Agent V2.csv actuals into elite_goals_reference.tsv.

Usage:
  python am_daily_dashboard/import_goals_reference_from_csv.py --month 8 --year 2026
  python am_daily_dashboard/import_goals_reference_from_csv.py --month 8 --dry-run

Reads column map from goals_q2_2026/calculate_q2_goals.py (MonthRow fields).
Merges into data/elite_goals_reference.tsv by (agent, year, month, day).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from am_daily_dashboard.goals import GOALS_AGENT_TAGS, TEAM_AGENT_TAG, parse_number  # noqa: E402

DEFAULT_CSV = Path(r"c:\Users\Owner\Downloads\Goals w Agent V2.csv")
REFERENCE_TSV = Path(__file__).resolve().parent / "data" / "elite_goals_reference.tsv"

HEADER = [
    "Agent Name",
    "month",
    "day",
    "year",
    "Daily Avg Purchase",
    "Daily Avg Net Purchase",
    "Monthly Players w purchase",
    "#Reactivations",
    "#Players Upgraded to Elite",
    "% Active From Portfolio",
    "ARPPU (avg purchase per paying player)",
]

ALLOWED = set(GOALS_AGENT_TAGS) | {TEAM_AGENT_TAG}


def open_csv(path: Path):
    raw = path.read_bytes()
    enc = "utf-16" if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff") else "utf-8-sig"
    return path.open(newline="", encoding=enc)


def fmt_money(v: float | None) -> str:
    if v is None:
        return ""
    return f"{v:,.2f}"


def fmt_pct(v: float | None) -> str:
    if v is None:
        return ""
    return f"{int(v)}%"


def fmt_count(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v))


def load_csv_rows(csv_path: Path, *, year: int, month: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with open_csv(csv_path) as f:
        sample = f.read(4096)
        f.seek(0)
        delim = "\t" if "\t" in sample.splitlines()[0] else ","
        reader = csv.DictReader(f, delimiter=delim)
        for rec in reader:
            agent = (rec.get("Agent Name") or "").strip()
            if not agent or agent.lower() == "total":
                continue
            try:
                m = int(parse_number(rec.get("Month*") or "0"))
                y = int(parse_number(rec.get("Year*") or "0"))
            except (TypeError, ValueError):
                continue
            if y != year or m != month:
                continue
            if agent not in ALLOWED:
                continue
            days = int(parse_number(rec.get("# Days Actual") or "0"))
            if days <= 0:
                continue
            purchase = parse_number(rec.get("Daily Avg Purchase Actual"))
            net = parse_number(rec.get("Daily Avg Net Purchase Actual"))
            purchasers = parse_number(rec.get("#Players w Purchase"))
            pct = parse_number(rec.get("% Active From Portfolio Actual (agent Ver)"))
            reactivations = parse_number(rec.get("#Reactivations Actual"))
            upgrades = parse_number(rec.get("#Players Upgraded Actual"))
            arppu = None
            if purchasers and purchase and purchasers > 0:
                arppu = (purchase * days) / purchasers
            rows.append(
                {
                    "Agent Name": agent,
                    "month": str(month),
                    "day": str(days),
                    "year": str(year),
                    "Daily Avg Purchase": fmt_money(purchase),
                    "Daily Avg Net Purchase": fmt_money(net),
                    "Monthly Players w purchase": fmt_count(purchasers),
                    "#Reactivations": fmt_count(reactivations),
                    "#Players Upgraded to Elite": fmt_count(upgrades),
                    "% Active From Portfolio": fmt_pct(pct),
                    "ARPPU (avg purchase per paying player)": fmt_money(arppu),
                }
            )
    return rows


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = "\t" if "\t" in sample.splitlines()[0] else ","
        return list(csv.DictReader(f, delimiter=delim))


def merge_rows(existing: list[dict[str, str]], incoming: list[dict[str, str]]) -> list[dict[str, str]]:
    key = lambda r: (
        r.get("Agent Name", ""),
        r.get("year", ""),
        r.get("month", ""),
        r.get("day", ""),
    )
    merged = {key(r): r for r in existing}
    for r in incoming:
        merged[key(r)] = r
    out = list(merged.values())
    out.sort(key=lambda r: (r.get("Agent Name", ""), r.get("year", ""), r.get("month", ""), int(r.get("day") or 0)))
    return out


def write_reference(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in HEADER})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=REFERENCE_TSV)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    incoming = load_csv_rows(args.csv, year=args.year, month=args.month)
    if not incoming:
        print(f"No rows for {args.year}-{args.month:02d} in {args.csv}")
        print("(Goals w Agent V2.csv currently has months 4-6 only — export month 8 from Tableau first.)")
        sys.exit(1)

    merged = merge_rows(read_existing(args.out), incoming)
    print(f"Importing {len(incoming)} row(s) for {args.year}-{args.month:02d}:")
    for r in incoming:
        print(f"  {r['Agent Name']} day={r['day']} purchase={r['Daily Avg Purchase']}")

    if args.dry_run:
        print("(dry-run — reference TSV not written)")
        return

    write_reference(args.out, merged)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
