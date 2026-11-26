from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from ledger.models import Transaction
from ledger.services import month_bounds

from .models import Budget

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def budget_summary(user, today, month=None):
    """Explain month-to-date spending against explicit monthly category limits.

    Future-dated records do not count as spending. Pacing is a linear comparison,
    not a prediction; a bill paid early can legitimately be ahead of pace.
    """
    month = (month or today).replace(day=1)
    start, end = month_bounds(month.year, month.month)
    days = end.day
    elapsed = max(0, min((today - start).days + 1, days))
    expenses = Transaction.objects.filter(
        user=user, kind=Transaction.EXPENSE, date__gte=start, date__lte=min(today, end)
    )
    spending = {
        item["category_id"]: item["spent"]
        for item in expenses.values("category_id").annotate(spent=Sum("amount"))
    }
    rows = []
    total_budget = total_spent = ZERO
    for budget in Budget.objects.filter(user=user, month=month).select_related("category"):
        spent = spending.pop(budget.category_id, ZERO)
        remaining = budget.amount - spent
        used = rounded(spent / budget.amount * 100)
        expected = rounded(budget.amount * Decimal(elapsed) / Decimal(days))
        if remaining < ZERO:
            status, label = "over", "Over budget"
        elif elapsed == 0:
            status, label = "planned", "Ready for next month"
        elif today > end:
            status, label = "within", "Within budget"
        elif spent > expected:
            status, label = "ahead", "Ahead of pace"
        else:
            status, label = "on-track", "On track"
        rows.append({
            "budget": budget,
            "category": budget.category,
            "amount": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "over_amount": max(-remaining, ZERO),
            "percent": min(used, Decimal("100")),
            "used_percent": used,
            "expected_spend": expected,
            "status": status,
            "status_label": label,
        })
        total_budget += budget.amount
        total_spent += spent
    return {
        "rows": rows,
        "month": month,
        "month_label": month.strftime("%B %Y"),
        "elapsed_days": elapsed,
        "days_in_month": days,
        "elapsed_percent": rounded(Decimal(elapsed) / Decimal(days) * 100),
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_remaining": total_budget - total_spent,
        "unbudgeted_spent": sum(spending.values(), ZERO),
        "over_count": sum(row["status"] == "over" for row in rows),
    }
