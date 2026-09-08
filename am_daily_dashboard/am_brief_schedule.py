"""Daily send calendar for the Elite AM Brief — every day of the week."""
from __future__ import annotations

from datetime import date, timedelta


def is_send_day(when: date | None = None) -> bool:
    """True every calendar day (Sun–Sat). Catch-up runs through yesterday."""
    return True


def report_date_for_send_day(when: date | None = None) -> date:
    """Report date (yesterday) for a scheduled send day."""
    return (when or date.today()) - timedelta(days=1)


def catch_up_through(when: date | None = None) -> date:
    """Last report date to include when catching up before today's send."""
    return report_date_for_send_day(when)
