"""
Elite Daily Summary — project entry point.

Run from repo root:
  python daily_summary/generate_daily_summary.py
  python daily_summary/generate_daily_summary.py --date YYYY-MM-DD

Output: daily_summary/daily_summaries/YYYY-MM-DD_elite_daily_summary.md
Canvas:  ~/.cursor/projects/.../canvases/elite-daily-summary-YYYY-MM-DD.canvas.tsx

Schedule: daily_summary/register_daily_summary_task.ps1 (10:00 Israel time).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "daily_summaries"

sys.path.insert(0, str(PROJECT_ROOT / "decline_check"))

import generate_daily_elite_summary as gen  # noqa: E402

gen.OUTPUT_DIR = OUTPUT_DIR


def main() -> None:
    gen.main()


if __name__ == "__main__":
    main()
