"""Post high-value Elite lock/TAB alerts to #big-players-account-closures."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from config import LOCK_TAB_SLACK_BOT_NAME, LOCK_TAB_SLACK_CHANNEL  # noqa: E402
from payload_builders import agent_display, lock_bucket  # noqa: E402
from queries import lock_tab_alert_sql  # noqa: E402
from am_brief_schedule import report_date_for_send_day  # noqa: E402
from daily_summary.generate_daily_elite_canvas import fmt_money_short  # noqa: E402
from elite_lib.bigquery import get_client, run_query  # noqa: E402
from elite_lib.console import use_utf8_stdout  # noqa: E402
from elite_lib.format import looker_account_portal_url  # noqa: E402
from elite_lib.slack_post import (  # noqa: E402
    SlackPostError,
    delete_message,
    find_channel_messages,
    post_message,
    resolve_token,
)

SENT_STATE = PACKAGE_DIR / "data" / "lock_tab_slack_sent.json"


def is_elite_send_day(when: date | None = None) -> bool:
    d = when or date.today()
    return d.weekday() in (6, 0, 1, 2, 3)


def resolve_report_date(arg: str | None) -> date:
    return date.fromisoformat(arg) if arg else report_date_for_send_day()


def resolve_slack_channel() -> str:
    import os

    env = os.environ.get("ELITE_LOCK_TAB_SLACK_CHANNEL")
    if env:
        return env.strip()
    try:
        from elite_lib._local_credentials import ELITE_LOCK_TAB_SLACK_CHANNEL  # type: ignore

        if ELITE_LOCK_TAB_SLACK_CHANNEL:
            return str(ELITE_LOCK_TAB_SLACK_CHANNEL).strip()
    except ImportError:
        pass
    return LOCK_TAB_SLACK_CHANNEL


def dedupe_key(row: dict) -> str:
    aid = int(row.get("AID") or 0)
    locked_at = row.get("locked_at")
    locked_at_s = locked_at.isoformat() if hasattr(locked_at, "isoformat") else str(locked_at or "")
    return f"{aid}:{locked_at_s}"


def load_state() -> tuple[set[str], dict[str, dict[str, str]]]:
    if not SENT_STATE.is_file():
        return set(), {}
    data = json.loads(SENT_STATE.read_text(encoding="utf-8"))
    return set(data.get("sent") or []), dict(data.get("posts") or {})


def save_state(sent: set[str], posts: dict[str, dict[str, str]]) -> None:
    SENT_STATE.parent.mkdir(parents=True, exist_ok=True)
    SENT_STATE.write_text(
        json.dumps({"sent": sorted(sent), "posts": posts}, indent=2) + "\n",
        encoding="utf-8",
    )


def filter_alert_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        bucket, _ = lock_bucket(
            str(row.get("lock_reason") or ""),
            str(row.get("lock_reason_comment") or ""),
        )
        if bucket != "Self-exclusion":
            out.append({**row, "bucket": bucket})
    return out


def format_hold_pct(hold_pct: object) -> str:
    try:
        return f"{100 * float(hold_pct):.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def format_lock_reason(lock_reason: str, lock_comment: str, fallback: str) -> str:
    reason = (lock_reason or "").strip()
    comment = (lock_comment or "").strip()
    if not reason and not comment:
        return fallback
    if not comment or reason.casefold() == comment.casefold():
        return reason or comment
    return f"{reason} — {comment}"


def format_alert_message(row: dict) -> str:
    aid = int(row.get("AID") or 0)
    bucket = row.get("bucket") or "Locked"
    looker = looker_account_portal_url(aid)
    name = row.get("name") or "n/a"
    name_line = f"• <{looker}|{name}>" if looker else f"• {name}"
    locked_at = row.get("locked_at")
    locked_s = locked_at.isoformat() if hasattr(locked_at, "isoformat") else str(locked_at or "")
    return "\n".join([
        "*Elite Lock Alert*",
        f"• AID: {aid}",
        name_line,
        f"• AM: {agent_display(str(row.get('agent') or ''))}",
        f"• Lock Date: {locked_s}",
        f"• Reason: {format_lock_reason(str(row.get('lock_reason') or ''), str(row.get('lock_reason_comment') or ''), bucket)}",
        f"• LTP {fmt_money_short(row.get('lifetime_purchased'))}",
        f"• Hold {format_hold_pct(row.get('hold_pct'))}",
        f"• 30D Purchase: {fmt_money_short(row.get('purchased_30d'))}",
    ])


def try_delete_prior(channel: str, row: dict, posts: dict[str, dict[str, str]]) -> None:
    key = dedupe_key(row)
    aid = str(int(row.get("AID") or 0))
    stored = posts.get(key) or {}
    if stored.get("ts"):
        try:
            delete_message(channel, stored["ts"])
            print(f"  Deleted prior post {key}")
            posts.pop(key, None)
            return
        except SlackPostError as exc:
            print(f"  Delete failed ({exc})", file=sys.stderr)
    try:
        for msg in find_channel_messages(channel):
            text = msg.get("text") or ""
            if aid in text and "elite lock alert" in text.lower() and (ts := msg.get("ts")):
                delete_message(channel, ts)
                print(f"  Deleted prior post {key} from history")
                posts.pop(key, None)
                return
    except SlackPostError:
        print("  Could not auto-delete old message — delete it manually in Slack.", file=sys.stderr)


def run(*, send: bool, report_date: date, force: bool = False, resend: bool = False) -> int:
    if not force and not is_elite_send_day():
        print("Skipped: not an Elite send day (Sun–Thu only).")
        return 0

    client = get_client()
    candidates = fetch_candidates(client, report_date)
    sent, posts = load_state()
    channel = resolve_slack_channel()

    if resend and send:
        for row in candidates:
            key = dedupe_key(row)
            if key in sent:
                try_delete_prior(channel, row, posts)
                sent.discard(key)

    pending = [r for r in candidates if dedupe_key(r) not in sent]
    print(f"Posting {len(pending)} alert(s)")
    if not pending:
        if send:
            save_state(sent, posts)
        return 0

    for row in pending:
        key = dedupe_key(row)
        text = format_alert_message(row)
        if not send:
            print(f"[dry-run] {key}\n{text}\n")
            continue
        if not resolve_token():
            return 1
        try:
            result = post_message(channel, text, username=LOCK_TAB_SLACK_BOT_NAME)
            sent.add(key)
            if ts := result.get("ts"):
                posts[key] = {"channel": channel, "ts": str(ts)}
            print(f"Posted {key}")
        except SlackPostError as exc:
            print(f"Slack failed: {exc}", file=sys.stderr)
            return 1

    if send:
        save_state(sent, posts)
    return 0


def fetch_candidates(client, report_date: date) -> list[dict]:
    return filter_alert_rows(run_query(client, lock_tab_alert_sql(report_date)))


def main() -> None:
    use_utf8_stdout()
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--resend", action="store_true")
    p.add_argument("--report-date", default="")
    a = p.parse_args()
    if not a.dry_run and not a.send:
        p.error("Pass --dry-run or --send")
    raise SystemExit(run(send=a.send, report_date=resolve_report_date(a.report_date or None), force=a.force, resend=a.resend))


if __name__ == "__main__":
    main()
