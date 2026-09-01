"""Daily Slack DM of the Elite AM Brief HTML to each AM (Sun-Thu, private).

Opt-in via AM_BRIEF_SLACK_ENABLED=1. Never posts to GitHub Pages.
Requires gitignored am_slack_recipients.local.json and SLACK_BOT_TOKEN.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from am_brief_schedule import is_send_day, report_date_for_send_day  # noqa: E402
from canvas_to_html import write_am_brief_html  # noqa: E402
from generate_am_daily_dashboard import (  # noqa: E402
    CURSOR_AUDIENCE_NAMES,
    GOALS_AM_ORDER,
    OUTPUT_DIR,
)
from goals import strip_payload_for_am  # noqa: E402

RECIPIENTS_PATH = PACKAGE_DIR / "data" / "am_slack_recipients.local.json"
SLACK_AM_ORDER = GOALS_AM_ORDER


def slack_enabled() -> bool:
    return os.environ.get("AM_BRIEF_SLACK_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def load_recipients() -> dict[str, str]:
    if not RECIPIENTS_PATH.is_file():
        raise SystemExit(
            f"Missing {RECIPIENTS_PATH.name}. Copy "
            f"am_slack_recipients.local.json.example and fill Slack user IDs."
        )
    data = json.loads(RECIPIENTS_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def run_catch_up() -> None:
    cmd = [
        sys.executable,
        str(PACKAGE_DIR / "generate_am_brief_range.py"),
        "--catch-up",
        "--verify",
    ]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def ensure_manager_json(report_date: date) -> Path:
    json_path = OUTPUT_DIR / f"{report_date.isoformat()}_elite_am_brief.json"
    if json_path.is_file():
        return json_path
    cmd = [
        sys.executable,
        str(PACKAGE_DIR / "generate_am_daily_dashboard.py"),
        "--date",
        report_date.isoformat(),
    ]
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    if not json_path.is_file():
        raise SystemExit(f"Generate did not produce {json_path}")
    return json_path


def human_date(d: date) -> str:
    return d.strftime("%a %d %b %Y")


def post_am_briefs(report_date: date, *, dry_run: bool = False) -> None:
    from elite_lib.slack_post import SlackPostError, post_dm_file

    json_path = ensure_manager_json(report_date)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    recipients = load_recipients()

    for slug in SLACK_AM_ORDER:
        name = CURSOR_AUDIENCE_NAMES[slug]
        user_id = recipients.get(name)
        if not user_id or user_id.startswith("U000"):
            print(f"Skip {name}: no Slack user id in {RECIPIENTS_PATH.name}")
            continue
        am_payload = strip_payload_for_am(payload, name)
        with tempfile.NamedTemporaryFile(
            suffix=".html", prefix=f"elite_am_brief_{slug}_", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)
        write_am_brief_html(am_payload, tmp_path)
        comment = f"Elite Dashboard · {human_date(report_date)}"
        if dry_run:
            print(f"Would DM {name} ({user_id}): {comment} [{tmp_path.name}]")
            tmp_path.unlink(missing_ok=True)
            continue
        try:
            post_dm_file(user_id, tmp_path, comment=comment)
            print(f"Slack DM sent to {name}")
        except SlackPostError as exc:
            print(f"Slack DM failed for {name}: {exc}", file=sys.stderr)
        finally:
            tmp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Slack DM Elite AM Brief to each AM")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-catch-up",
        action="store_true",
        help="Do not run generate_am_brief_range --catch-up first",
    )
    args = parser.parse_args()

    today = date.today()
    if not args.dry_run and not is_send_day(today):
        print(f"Skip: AM Brief Slack runs Sun-Thu only (today is {today:%A}).")
        return

    if not args.dry_run and not slack_enabled():
        print("Skip: AM_BRIEF_SLACK_ENABLED is not set.")
        return

    if not args.skip_catch_up and not args.dry_run:
        run_catch_up()

    report_date = (
        date.fromisoformat(args.date) if args.date else report_date_for_send_day(today)
    )
    post_am_briefs(report_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
