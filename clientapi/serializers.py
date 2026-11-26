from decimal import Decimal

from django.utils import timezone

from budgets.services import budget_summary
from ledger.models import Account, Category, Transaction
from planning.forecast import required_monthly
from planning.models import RecurringItem, SavingsGoal


def money(value):
    return format(Decimal(value), ".2f") if value is not None else None


def iso(value):
    return value.isoformat() if value is not None else None


def event_record(event):
    day, name, amount = event
    return {"date": iso(day), "name": name, "amount": money(amount)}


def budget_record(row):
    budget = row["budget"]
    return {
        "id": budget.pk, "category": budget.category_id,
        "category_name": budget.category.name, "month": budget.month.strftime("%Y-%m"),
        **{key: money(row[key]) for key in ("amount", "spent", "remaining", "over_amount", "percent")},
        "status": row["status"], "status_label": row["status_label"],
    }


def budget_snapshot(user, today, month=None):
    summary = budget_summary(user, today, month)
    return {
        "month": summary["month"].strftime("%Y-%m"), "month_label": summary["month_label"],
        **{key: money(summary[key]) for key in (
            "total_budget", "total_spent", "total_remaining", "unbudgeted_spent", "elapsed_percent",
        )},
        "over_count": summary["over_count"],
        "rows": [budget_record(row) for row in summary["rows"]],
    }


def record(instance, today=None):
    today = today or timezone.localdate()
    if isinstance(instance, Account):
        return {"id": instance.pk, "name": instance.name, "opening_balance": money(instance.opening_balance), "balance": money(instance.balance)}
    if isinstance(instance, Category):
        return {"id": instance.pk, "name": instance.name, "kind": instance.kind}
    if isinstance(instance, Transaction):
        return {
            "id": instance.pk, "kind": instance.kind, "amount": money(instance.amount),
            "date": iso(instance.date), "description": instance.description,
            "account": instance.account_id, "to_account": instance.to_account_id, "category": instance.category_id,
            "account_name": instance.account.name,
            "to_account_name": instance.to_account.name if instance.to_account_id else None,
            "category_name": instance.category.name if instance.category_id else None,
        }
    if isinstance(instance, SavingsGoal):
        return {
            "id": instance.pk, "name": instance.name,
            "target_amount": money(instance.target_amount), "saved_so_far": money(instance.saved_so_far),
            "target_date": iso(instance.target_date), "remaining": money(instance.remaining),
            "monthly_required": money(required_monthly(instance.remaining, today, instance.target_date)),
            "percent": min(int(instance.saved_so_far / instance.target_amount * 100), 100),
        }
    if isinstance(instance, RecurringItem):
        return {
            "id": instance.pk, "name": instance.name, "kind": instance.kind, "amount": money(instance.amount),
            "frequency": instance.frequency, "next_date": iso(instance.next_date),
            "end_date": iso(instance.end_date), "active": instance.active,
        }
    # Budget values are calculated from owned records by the existing service.
    return next(row for row in budget_snapshot(instance.user, today, instance.month)["rows"] if row["id"] == instance.pk)


def forecast_record(result, daily, estimated):
    low_date, low_amount = result.min_point("expected")
    return {
        "days": len(result.dates) - 1,
        "start_balance": money(result.expected[0]), "daily_spend": money(daily),
        "estimated_daily_spend": money(estimated),
        "end_expected": money(result.expected[-1]), "end_low": money(result.low[-1]), "end_high": money(result.high[-1]),
        "lowest_date": iso(low_date), "lowest_value": money(low_amount),
        "shortfall_expected": iso(result.first_below_zero("expected")), "shortfall_low": iso(result.first_below_zero("low")),
        "dates": [iso(day) for day in result.dates],
        **{name: [money(value) for value in getattr(result, name)] for name in ("expected", "low", "high")},
        "events": [event_record(event) for event in result.events],
    }
