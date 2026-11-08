"""Explainable cash-flow forecasting. Pure Python + Decimal: no database access here.

Rules (kept deliberately simple and transparent):
  1. Start from today's real balance. Events dated today or earlier are assumed already recorded.
  2. Add every recurring income / bill on its due date (monthly items keep their day of month,
     clamped to month length; weekly items repeat every 7 days).
  3. Subtract an estimated daily amount for everyday spending.
  4. Show a range: spending +/- `spread` (default 25%) gives the low (cautious) and high (optimistic) paths.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from ledger.dates import add_months

CENT = Decimal("0.01")
ZERO = Decimal("0")
INCOME = "income"
EXPENSE = "expense"
MONTHLY = "monthly"
WEEKLY = "weekly"
DAYS_PER_MONTH = Decimal("30.4375")


def q(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Recurring:
    name: str
    kind: str  # INCOME or EXPENSE
    amount: Decimal  # always positive
    frequency: str  # MONTHLY or WEEKLY
    next_date: date  # any known occurrence; later ones are derived from it
    end_date: date = None


@dataclass(frozen=True)
class OneOff:
    name: str
    amount: Decimal  # signed: negative reduces the balance
    on: date


@dataclass
class Forecast:
    dates: list
    expected: list
    low: list
    high: list
    events: list  # (date, name, signed amount)

    def min_point(self, series="expected"):
        values = getattr(self, series)
        index = min(range(len(values)), key=values.__getitem__)
        return self.dates[index], values[index]

    def first_below_zero(self, series="expected"):
        for day, value in zip(self.dates, getattr(self, series)):
            if value < 0:
                return day
        return None


def occurrences(item, start, end):
    """Dates in [start, end] on which a recurring item falls."""
    found = []
    step = 0
    while True:
        if item.frequency == WEEKLY:
            day = item.next_date + timedelta(weeks=step)
        else:
            day = add_months(item.next_date, step)
        if day > end or (item.end_date and day > item.end_date):
            return found
        if day >= start:
            found.append(day)
        step += 1


def daily_equivalent(item):
    """Average per-day cost of a recurring item."""
    per_year = Decimal(52) if item.frequency == WEEKLY else Decimal(12)
    return item.amount * per_year / Decimal(365)


def build_forecast(start_balance, start, horizon_days, recurring=(), daily_spend=ZERO, one_offs=(), spread=Decimal("0.25")):
    """Project the balance for `horizon_days` days after `start`.

    One-off items dated on or before `start` are applied on the first projected day.
    """
    daily_spend = max(Decimal(daily_spend), ZERO)
    first_day = start + timedelta(days=1)
    last_day = start + timedelta(days=horizon_days)

    by_day = defaultdict(list)
    for item in recurring:
        sign = 1 if item.kind == INCOME else -1
        for day in occurrences(item, first_day, last_day):
            by_day[day].append((item.name, sign * item.amount))
    for one_off in one_offs:
        day = max(one_off.on, first_day)
        if day <= last_day:
            by_day[day].append((one_off.name, one_off.amount))

    balance = {"expected": Decimal(start_balance), "low": Decimal(start_balance), "high": Decimal(start_balance)}
    spend = {
        "expected": daily_spend,
        "low": daily_spend * (1 + spread),
        "high": daily_spend * (1 - spread),
    }
    result = Forecast(
        dates=[start],
        expected=[q(start_balance)],
        low=[q(start_balance)],
        high=[q(start_balance)],
        events=[],
    )
    for offset in range(1, horizon_days + 1):
        day = start + timedelta(days=offset)
        todays = by_day.get(day, [])
        net = sum((amount for _, amount in todays), ZERO)
        result.dates.append(day)
        for series in ("expected", "low", "high"):
            balance[series] += net - spend[series]
            getattr(result, series).append(q(balance[series]))
        result.events.extend((day, name, q(amount)) for name, amount in todays)
    return result


def required_monthly(remaining, today, target_date):
    """Monthly amount needed to reach a goal by `target_date`; None if the date has passed."""
    if remaining <= 0:
        return q(0)
    days_left = (target_date - today).days
    if days_left <= 0:
        return None
    months = max(Decimal(days_left) / DAYS_PER_MONTH, Decimal(1))
    return (Decimal(remaining) / months).quantize(CENT, rounding=ROUND_CEILING)
