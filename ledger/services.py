import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from .dates import add_months
from .models import Account, Category, Transaction

ZERO = Decimal("0.00")

DEFAULT_CATEGORIES = [
    ("Salary", Transaction.INCOME),
    ("Other income", Transaction.INCOME),
    ("Housing", Transaction.EXPENSE),
    ("Utilities", Transaction.EXPENSE),
    ("Food", Transaction.EXPENSE),
    ("Transport", Transaction.EXPENSE),
    ("Entertainment", Transaction.EXPENSE),
    ("Health", Transaction.EXPENSE),
    ("Education", Transaction.EXPENSE),
    ("Other", Transaction.EXPENSE),
]


def create_default_categories(user):
    Category.objects.bulk_create(
        [Category(user=user, name=name, kind=kind) for name, kind in DEFAULT_CATEGORIES],
        ignore_conflicts=True,
    )


def total_balance(user):
    """Sum of all account balances. Transfers between own accounts net to zero."""
    return sum((a.balance for a in Account.objects.filter(user=user)), ZERO)


def month_bounds(year, month):
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def totals_between(user, start, end):
    """(income, expense) for a date range. Transfers are excluded on purpose."""
    result = (
        Transaction.objects.filter(user=user, date__gte=start, date__lte=end)
        .exclude(kind=Transaction.TRANSFER)
        .aggregate(
            income=Sum("amount", filter=Q(kind=Transaction.INCOME)),
            expense=Sum("amount", filter=Q(kind=Transaction.EXPENSE)),
        )
    )
    return result["income"] or ZERO, result["expense"] or ZERO


def expense_breakdown(user, start, end):
    rows = (
        Transaction.objects.filter(user=user, kind=Transaction.EXPENSE, date__gte=start, date__lte=end)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    return [(row["category__name"] or "Uncategorized", row["total"]) for row in rows]


def monthly_history(user, today, months=6):
    first = today.replace(day=1)
    history = []
    for offset in range(months - 1, -1, -1):
        start = add_months(first, -offset)
        _, end = month_bounds(start.year, start.month)
        income, expense = totals_between(user, start, end)
        history.append({"label": start.strftime("%b %Y"), "income": income, "expense": expense})
    return history
