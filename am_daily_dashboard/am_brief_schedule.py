"""Sun-Thu send calendar for the Elite AM Brief (matches daily summary schedule)."""
from __future__ import annotations

from datetime import date, timedelta

# Python weekday(): Monday=0 … Sunday=6
_SEND_WEEKDAYS = frozenset({6, 0, 1, 2, 3})


def is_send_day(when: date | None = None) -> bool:
    """True on Sunday through Thursday (Israel morning send days)."""
    d = when or date.today()
    return d.weekday() in _SEND_WEEKDAYS


def report_date_for_send_day(when: date | None = None) -> date:
    """Report date (yesterday) for a scheduled send day."""
    return (when or date.today()) - timedelta(days=1)


def catch_up_through(when: date | None = None) -> date:
    """Last report date to include when catching up before today's send."""
    return report_date_for_send_day(when)
