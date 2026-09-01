"""Email the monthly trigger summary Excel to Alon on the 1st (opt-in).

Requires gitignored SMTP settings in elite_lib/_local_credentials.py:

    SMTP_HOST = "smtp.office365.com"
    SMTP_PORT = 587
    SMTP_USER = "..."
    SMTP_PASSWORD = "..."
    MONTHLY_TRIGGER_TO = "Alon@silversocialgames.com"
"""
from __future__ import annotations

import argparse
import calendar
import smtplib
import subprocess
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
MONTHLY_DIR = PROJECT_ROOT / "monthly_summaries"
sys.path.insert(0, str(PROJECT_ROOT))


def _smtp_settings() -> tuple[str, int, str, str, str]:
    try:
        from elite_lib import _local_credentials as creds  # type: ignore
    except ImportError as exc:
        raise SystemExit("Missing elite_lib/_local_credentials.py for SMTP.") from exc
    host = getattr(creds, "SMTP_HOST", None)
    port = int(getattr(creds, "SMTP_PORT", 587))
    user = getattr(creds, "SMTP_USER", None)
    password = getattr(creds, "SMTP_PASSWORD", None)
    to_addr = getattr(creds, "MONTHLY_TRIGGER_TO", "Alon@silversocialgames.com")
    if not all([host, user, password]):
        raise SystemExit("SMTP_HOST, SMTP_USER, and SMTP_PASSWORD required in _local_credentials.py")
    return str(host), port, str(user), str(password), str(to_addr)


def prior_month(today: date | None = None) -> str:
    d = today or date.today()
    if d.month == 1:
        return f"{d.year - 1}-12"
    return f"{d.year}-{d.month - 1:02d}"


def send_monthly(month: str, *, dry_run: bool = False) -> None:
    stem = f"{month}_elite_trigger_summary"
    xlsx = MONTHLY_DIR / f"{stem}.xlsx"
    csv_path = MONTHLY_DIR / f"{stem}.csv"
    attach = xlsx if xlsx.is_file() else csv_path
    if not attach.is_file():
        raise SystemExit(f"No summary file for {month}. Run generate_monthly_trigger_summary first.")

    host, port, user, password, to_addr = _smtp_settings()
    msg = EmailMessage()
    msg["Subject"] = f"Elite Dashboard trigger summary · {month}"
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(
        f"Attached: monthly trigger rollup for {month}.\n"
        "Counts sum daily focus badges across archived manager briefs."
    )
    msg.add_attachment(
        attach.read_bytes(),
        maintype="application",
        subtype="octet-stream",
        filename=attach.name,
    )
    if dry_run:
        print(f"Would email {attach.name} to {to_addr} via {host}")
        return
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"Emailed {attach.name} to {to_addr}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Email monthly trigger summary")
    parser.add_argument("--month", help="YYYY-MM (default: prior calendar month on 1st runs)")
    parser.add_argument("--generate", action="store_true", help="Generate files before sending")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    month = args.month or prior_month()
    if args.generate:
        subprocess.run(
            [
                sys.executable,
                str(PACKAGE_DIR / "generate_monthly_trigger_summary.py"),
                "--month",
                month,
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )
    send_monthly(month, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
