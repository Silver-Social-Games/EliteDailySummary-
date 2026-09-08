"""Zip an AM Brief audience folder for one-time bootstrap delivery.

Use when an AM needs full calendar history offline (Slack/ email attachment).
Daily sends after that are single HTML files via post_am_brief_slack.py.

  python am_daily_dashboard/package_am_brief.py --agent Coral
  python am_daily_dashboard/package_am_brief.py --all
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PACKAGE_DIR))

from mirror_am_brief import SLUG_TO_FOLDER, am_brief_share_dir  # noqa: E402
from elite_lib.export_paths import cursor_export_dir  # noqa: E402

AM_NAMES = [name for name in SLUG_TO_FOLDER.values() if name != "Manager"]


def package_agent(agent_name: str, *, dest_dir: Path | None = None) -> Path:
    src = am_brief_share_dir(agent_name=agent_name)
    if src is None or not src.is_dir():
        raise SystemExit(f"No Elite_Cursor folder for {agent_name}")
    html_files = sorted(src.glob("*.html"))
    if not html_files:
        raise SystemExit(f"No HTML files in {src}")

    out_base = dest_dir or cursor_export_dir("am_brief") or src.parent
    out_base.mkdir(parents=True, exist_ok=True)
    zip_base = out_base / f"Elite_AM_Brief_{agent_name}"
    if zip_base.with_suffix(".zip").exists():
        zip_base.with_suffix(".zip").unlink()
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=src)
    size_mb = Path(archive).stat().st_size / (1024 * 1024)
    print(f"Packaged {len(html_files)} HTML file(s) for {agent_name}")
    print(f"  {archive} ({size_mb:.1f} MB)")
    print(
        "  Send via Slack DM (upload zip). AM unzips to Documents\\Elite AM Brief\\"
        f"{agent_name}\\ and opens elite_am_brief_{agent_name.lower()}.html in Chrome."
    )
    return Path(archive)


def main() -> None:
    parser = argparse.ArgumentParser(description="Zip AM Brief folder for bootstrap delivery")
    parser.add_argument("--agent", help="One AM: Coral, Gabriel, Lee, or Rachel")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Package all four AM folders",
    )
    args = parser.parse_args()
    if args.all:
        for name in AM_NAMES:
            package_agent(name)
        return
    if not args.agent:
        raise SystemExit("Provide --agent Coral or --all")
    package_agent(args.agent.strip())


if __name__ == "__main__":
    main()
