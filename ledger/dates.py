import calendar
from datetime import date


def add_months(d: date, months: int) -> date:
    """Shift a date by whole months, clamping the day to the target month's length."""
    index = d.month - 1 + months
    year = d.year + index // 12
    month = index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
