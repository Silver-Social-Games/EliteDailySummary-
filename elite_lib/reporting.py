"""Shared report comparison helpers."""

from __future__ import annotations

from datetime import date


def day_row(rows: list[dict], report_date: date) -> dict:
    """Return the row matching a calendar date, or an empty mapping."""
    iso_date = report_date.isoformat()
    return next(
        (row for row in rows if str(row.get("date"))[:10] == iso_date),
        {},
    )


def wow_change(current: float, prior: float) -> tuple[float, float]:
    """Return absolute and percentage change from the prior value."""
    change = current - prior
    percentage = (change / prior * 100) if prior else 0.0
    return change, percentage
