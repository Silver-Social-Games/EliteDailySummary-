"""DM each AM their Elite AM Brief HTML for the report date.

Delivery (pick one):
  *OneDrive sync (zero daily action for you or AM after setup):* scheduled
   generate + mirror updates VIP\\Elite_Cursor\\AM Brief\\{AM}\\; share that
   folder View-only; AM syncs via OneDrive desktop app and opens from File Explorer.
  *Slack (fallback):* --bootstrap-if-needed once, then --send daily.

Run from repo root:
  python am_daily_dashboard/post_am_brief_slack.py --dry-run
  python am_daily_dashboard/post_am_brief_slack.py --send
  python am_daily_dashboard/post_am_brief_slack.py --send --bootstrap-if-needed
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from mirror_am_brief import am_brief_share_dir  # noqa: E402
from package_am_brief import package_agent  # noqa: E402
from elite_lib.console import use_utf8_stdout  # noqa: E402
from elite_lib.slack_post import SlackPostError, open_dm, resolve_token, upload_file  # noqa: E402

RECIPIENTS_TSV = PACKAGE_DIR / "data" / "am_brief_slack_recipients.tsv"
BOOTSTRAP_STATE = PACKAGE_DIR / "data" / "am_brief_slack_bootstrap.json"
WORKSHOP_EXPORTS = PACKAGE_DIR / "exports"

OPEN_INSTRUCTIONS = (
    "1. *Download* the attached file(s) (Save, not preview)\n"
    "2. Put them in your local *Elite AM Brief* folder (same folder every day)\n"
    "3. Double-click *elite_am_brief_{slug}.html* in Chrome or Edge\n"
    "Never open inside Slack preview or OneDrive web view."
)

BOOTSTRAP_INSTRUCTIONS = (
    "*First-time only:* unzip the attached zip to e.g. "
    "Documents\\Elite AM Brief\\{agent}\\. "
    "Open elite_am_brief_{slug}.html from that folder. "
    "Each morning, save new attachments into the *same* folder so the calendar keeps working."
)

def resolve_report_date(arg: str | None) -> date:
    if arg:
        return date.fromisoformat(arg)
    return date.today() - timedelta(days=1)


def load_recipients(*, agent: str = "") -> list[dict[str, str]]:
    if not RECIPIENTS_TSV.is_file():
        raise SystemExit(
            f"Recipients file missing: {RECIPIENTS_TSV}\n"
            "Copy data/am_brief_slack_recipients.tsv.example and fill Slack user ids."
        )
    rows: list[dict[str, str]] = []
    with RECIPIENTS_TSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if (row.get("enabled") or "").strip().lower() not in ("yes", "y", "1", "true"):
                continue
            name = (row.get("agent") or "").strip()
            slug = (row.get("slug") or "").strip().lower()
            user_id = (row.get("slack_user_id") or "").strip()
            if not name or not slug or not user_id:
                continue
            if agent and name.lower() != agent.strip().lower():
                continue
            rows.append({"agent": name, "slug": slug, "slack_user_id": user_id})
    if not rows:
        hint = f" for {agent}" if agent else ""
        raise SystemExit(f"No enabled recipients{hint} in {RECIPIENTS_TSV}")
    return rows


def brief_html_paths(report_date: date, agent: str, slug: str) -> tuple[Path | None, Path | None]:
    """Return (dated, bookmark) paths for an AM audience."""
    dated_name = f"{report_date.isoformat()}_elite_am_brief_{slug}.html"
    bookmark_name = f"elite_am_brief_{slug}.html"
    share_dir = am_brief_share_dir(agent_name=agent)
    dated: Path | None = None
    bookmark: Path | None = None
    if share_dir is not None:
        if (share_dir / dated_name).is_file():
            dated = share_dir / dated_name
        if (share_dir / bookmark_name).is_file():
            bookmark = share_dir / bookmark_name
    if dated is None and (WORKSHOP_EXPORTS / dated_name).is_file():
        dated = WORKSHOP_EXPORTS / dated_name
    return dated, bookmark


def load_bootstrap_state() -> dict[str, bool]:
    if not BOOTSTRAP_STATE.is_file():
        return {}
    try:
        raw = json.loads(BOOTSTRAP_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def save_bootstrap_state(state: dict[str, bool]) -> None:
    BOOTSTRAP_STATE.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def build_daily_message(agent: str, slug: str, report_date: date) -> str:
    subtitle = report_date.strftime("%A %d %b %Y")
    return "\n".join(
        [
            f"*Elite AM Brief* — {subtitle}",
            "",
            f"Hi {agent} — your morning board is attached.",
            "",
            "*How to open:*",
            OPEN_INSTRUCTIONS.format(slug=slug),
            "",
            "Save today's file(s) into the same folder as your history zip, then open "
            f"`elite_am_brief_{slug}.html` for the calendar.",
        ]
    )


def build_bootstrap_message(agent: str, slug: str) -> str:
    return "\n".join(
        [
            f"*Elite AM Brief — one-time setup*",
            "",
            f"Hi {agent} — attached is your full brief history (zip).",
            "",
            BOOTSTRAP_INSTRUCTIONS.format(agent=agent, slug=slug),
            "",
            OPEN_INSTRUCTIONS.format(slug=slug),
        ]
    )


def send_bootstrap(
    recipient: dict[str, str],
    *,
    dry_run: bool,
    token: str | None,
    force: bool,
) -> bool:
    """Send history zip once per AM. Returns True if sent (or would send)."""
    agent = recipient["agent"]
    state = load_bootstrap_state()
    if state.get(agent) and not force:
        print(f"  Bootstrap skip {agent} (already sent)")
        return False
    zip_path = package_agent(agent)
    message = build_bootstrap_message(agent, recipient["slug"])
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}Bootstrap {agent}: {zip_path.name} ({size_mb:.1f} MB)")
    if dry_run:
        return True
    channel_id = open_dm(recipient["slack_user_id"], token=token)
    upload_file(
        zip_path,
        channel_id,
        comment=message,
        title=f"Elite AM Brief setup — {agent}",
        token=token,
    )
    state[agent] = True
    save_bootstrap_state(state)
    print(f"  Bootstrap sent to DM {channel_id}")
    return True


def post_daily_for_am(
    recipient: dict[str, str],
    report_date: date,
    *,
    dry_run: bool,
    token: str | None,
) -> None:
    slug = recipient["slug"]
    dated, bookmark = brief_html_paths(report_date, recipient["agent"], slug)
    if dated is None:
        raise SystemExit(
            f"No per-AM brief for {recipient['agent']} on {report_date.isoformat()}. "
            "Run generate_am_daily_dashboard.py for that date first."
        )
    paths = [dated]
    if bookmark and bookmark.resolve() != dated.resolve():
        paths.append(bookmark)
    message = build_daily_message(recipient["agent"], slug, report_date)
    prefix = "[DRY RUN] " if dry_run else ""
    names = ", ".join(p.name for p in paths)
    total_kb = sum(p.stat().st_size for p in paths) // 1024
    print(
        f"{prefix}{recipient['agent']} ({recipient['slack_user_id']}): "
        f"{names} ({total_kb} KB)"
    )
    if dry_run:
        return
    channel_id = open_dm(recipient["slack_user_id"], token=token)
    for i, path in enumerate(paths):
        upload_file(
            path,
            channel_id,
            comment=message if i == 0 else "",
            title=f"Elite AM Brief — {report_date.isoformat()}",
            token=token,
        )
    print(f"  Sent to DM {channel_id}")


def main() -> None:
    use_utf8_stdout()
    parser = argparse.ArgumentParser(description="DM Elite AM Brief HTML to each AM")
    parser.add_argument("--date", help="Report date YYYY-MM-DD (default: yesterday)")
    parser.add_argument(
        "--agent",
        help="Send to one AM only (e.g. Coral)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print recipients and message text without calling Slack (default)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Upload the HTML to each AM's Slack DM",
    )
    parser.add_argument(
        "--bootstrap-if-needed",
        action="store_true",
        help="Send history zip once per AM (tracked in data/am_brief_slack_bootstrap.json)",
    )
    parser.add_argument(
        "--force-bootstrap",
        action="store_true",
        help="Re-send history zip even if bootstrap was already sent",
    )
    args = parser.parse_args()
    dry_run = not args.send
    report_date = resolve_report_date(args.date)
    token = None if dry_run else resolve_token()
    if not dry_run and not token:
        raise SystemExit(
            "No Slack bot token configured. Use --dry-run to preview, or set "
            "SLACK_BOT_TOKEN / elite_lib/_local_credentials.py before --send."
        )

    recipients = load_recipients(agent=args.agent or "")
    mode = "DRY RUN" if dry_run else "SEND"
    print(f"Elite AM Brief Slack — {report_date.isoformat()} ({mode})")
    errors = 0
    if args.bootstrap_if_needed or args.force_bootstrap:
        print("\nBootstrap (history zip)")
        for recipient in recipients:
            try:
                send_bootstrap(
                    recipient,
                    dry_run=dry_run,
                    token=token,
                    force=args.force_bootstrap,
                )
            except (SlackPostError, SystemExit) as exc:
                errors += 1
                print(f"  ERROR bootstrap {recipient['agent']}: {exc}")
    print("\nDaily brief")
    for recipient in recipients:
        try:
            post_daily_for_am(
                recipient,
                report_date,
                dry_run=dry_run,
                token=token,
            )
        except (SlackPostError, SystemExit) as exc:
            errors += 1
            print(f"  ERROR: {recipient['agent']}: {exc}")
    if errors:
        raise SystemExit(f"{errors} recipient(s) failed")
    if dry_run:
        print("\nDry run complete. Re-run with --send to post to Slack.")


if __name__ == "__main__":
    main()
