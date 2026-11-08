"""Glue between the database and the pure forecast functions."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Min, Q, Sum

from ledger.models import Transaction

from .forecast import DAYS_PER_MONTH, EXPENSE, Recurring, daily_equivalent, q
from .models import RecurringItem

ZERO = Decimal("0")


def recurring_items(user):
    return [
        Recurring(r.name, r.kind, r.amount, r.frequency, r.next_date, r.end_date)
        for r in RecurringItem.objects.filter(user=user, active=True)
    ]


def _history(user, today, window):
    """(income, expense, covered_days) over the last `window` days, transfers excluded."""
    since = today - timedelta(days=window)
    own = Transaction.objects.filter(user=user, date__gt=since, date__lte=today).exclude(kind=Transaction.TRANSFER)
    totals = own.aggregate(
        income=Sum("amount", filter=Q(kind=Transaction.INCOME)),
        expense=Sum("amount", filter=Q(kind=Transaction.EXPENSE)),
        first=Min("date"),
    )
    if totals["first"] is None:
        return ZERO, ZERO, 0
    covered = (today - totals["first"]).days + 1
    return totals["income"] or ZERO, totals["expense"] or ZERO, covered


def estimate_daily_spend(user, today, window=90):
    """Average daily spending, minus the recurring bills already modelled separately.

    Uses only the days since the user's first recent transaction, so new users are not
    underestimated. Never negative.
    """
    _, expense, covered = _history(user, today, window)
    if covered == 0:
        return q(0)
    average = expense / Decimal(covered)
    bills = sum((daily_equivalent(r) for r in recurring_items(user) if r.kind == EXPENSE), ZERO)
    return q(max(average - bills, ZERO))


def estimate_monthly_surplus(user, today, window=90):
    """Average (income - expenses) per month over recent history; may be negative."""
    income, expense, covered = _history(user, today, window)
    if covered == 0:
        return q(0)
    return q((income - expense) / Decimal(covered) * DAYS_PER_MONTH)
