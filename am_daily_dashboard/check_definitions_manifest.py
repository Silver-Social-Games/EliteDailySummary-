"""Detect AM Brief definition drift (queries, config, goals, web bundle).

Committed manifest stores SHA-256 hashes only. Run after generator edits:

  python am_daily_dashboard/check_definitions_manifest.py
  python am_daily_dashboard/check_definitions_manifest.py --update
  python am_daily_dashboard/check_definitions_manifest.py --slack
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
MANIFEST_PATH = PACKAGE_DIR / "data" / "definitions_manifest.json"

WATCHED: list[tuple[str, Path]] = [
    ("config.py", PACKAGE_DIR / "config.py"),
    ("queries.py", PACKAGE_DIR / "queries.py"),
    ("goals.py", PACKAGE_DIR / "goals.py"),
    ("payload_builders.py", PACKAGE_DIR / "payload_builders.py"),
    ("elite_goals.tsv", PACKAGE_DIR / "data" / "elite_goals.tsv"),
    ("elite_am_brief_web.html", PACKAGE_DIR / "handoffs" / "elite_am_brief_web.html"),
]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def current_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for label, path in WATCHED:
        if not path.is_file():
            raise SystemExit(f"Missing watched file: {path}")
        out[label] = file_sha256(path)
    return out


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {"version": 1, "files": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(data: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {MANIFEST_PATH.relative_to(PROJECT_ROOT)}")


def slack_alert(changed: list[str]) -> None:
    try:
        from elite_lib.slack_post import SlackPostError, post_dm_message, resolve_manager_user_id
    except ImportError:
        print("Slack helper unavailable; skipping alert.", file=sys.stderr)
        return
    user_id = resolve_manager_user_id()
    if not user_id:
        print("No manager Slack user id configured; skipping alert.", file=sys.stderr)
        return
    files = ", ".join(changed)
    text = f"AM Brief definitions changed: {files}. Reconcile before trusting numbers."
    try:
        post_dm_message(user_id, text)
        print(f"Slack alert sent to {user_id}")
    except SlackPostError as exc:
        print(f"Slack alert failed: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check AM Brief definition manifest")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write current hashes to definitions_manifest.json",
    )
    parser.add_argument(
        "--slack",
        action="store_true",
        help="On drift, DM the manager (requires local Slack config)",
    )
    args = parser.parse_args()

    current = current_hashes()
    if args.update:
        save_manifest({"version": 1, "files": current})
        return

    manifest = load_manifest()
    saved = manifest.get("files") or {}
    changed = [label for label, digest in current.items() if saved.get(label) != digest]
    missing = [label for label in saved if label not in current]

    if not saved:
        print("No manifest baseline yet. Run with --update after verifying a good run.")
        raise SystemExit(1)

    if changed or missing:
        print("DEFINITION DRIFT detected:")
        for label in changed:
            print(f"  changed: {label}")
        for label in missing:
            print(f"  removed from watch list: {label}")
        if args.slack:
            slack_alert(changed + missing)
        raise SystemExit(1)

    print("PASS: all watched definition files match the committed manifest.")


if __name__ == "__main__":
    main()
