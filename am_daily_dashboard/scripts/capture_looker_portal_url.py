"""Print Looker Account Portal URLs for manual verification on dashboard 5207.

Usage:
  python am_daily_dashboard/scripts/capture_looker_portal_url.py 123456789

After changing DEFAULT_LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE in elite_lib/format.py
(or LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE in web/src/looker.ts), open each URL,
confirm Purchase filter date shows 30 day (not 7).

To discover the correct token: open dashboard 5207, set timeframe to Last 30 Days,
copy the browser address bar, and paste the query string into
am_daily_dashboard/data/looker_account_portal_query.tsv (see LOOKER_ACCOUNT_PORTAL.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from elite_lib.format import (  # noqa: E402
    DEFAULT_LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE,
    looker_account_portal_url,
)


def main() -> None:
    aid = sys.argv[1] if len(sys.argv) > 1 else "123456789"
    url = looker_account_portal_url(aid)
    print(f"purchase date token: {DEFAULT_LOOKER_ACCOUNT_PORTAL_PURCHASE_DATE}")
    print(url)


if __name__ == "__main__":
    main()
