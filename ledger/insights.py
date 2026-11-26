"""Small, auditable dashboard insights; no model or third-party data required."""
from datetime import timedelta
from decimal import Decimal

from budgets.services import budget_summary
from ledger.dates import add_months
from ledger.services import expense_breakdown, total_balance
from planning.forecast import build_forecast, q
from planning.models import SavingsGoal
from planning.services import estimate_daily_spend, recurring_items


def dashboard_insights(user, today, breakdown):
    daily = estimate_daily_spend(user, today)
    forecast = build_forecast(total_balance(user), today, 30, recurring_items(user), daily)
    previous_start = add_months(today.replace(day=1), -1)
    previous_end = add_months(today, -1)
    previous = dict(expense_breakdown(user, previous_start, previous_end))
    alerts = []
    for name, amount in breakdown:
        baseline = previous.get(name, Decimal(0))
        if baseline > 0 and amount - baseline >= 100 and amount > baseline * Decimal('1.25'):
            alerts.append({'category': name, 'change': q(amount - baseline),
                           'percent': round((amount / baseline - 1) * 100)})
    goals = []
    for goal in SavingsGoal.objects.filter(user=user)[:3]:
        goals.append({'goal': goal, 'percent': min(100, round(goal.saved_so_far / goal.target_amount * 100))})
    colors = ['#174e40', '#78ae92', '#bacf84', '#e2ba78', '#9b9fc5', '#87bdc6', '#ba9d8d', '#a8b1b0']
    total_expense = sum((v for _, v in breakdown), Decimal(0))
    categories = [{'name': name, 'amount': value, 'color': colors[i % len(colors)],
                   'percent': round(value / total_expense * 100) if total_expense else 0}
                  for i, (name, value) in enumerate(breakdown)]
    return {
        'outlook': forecast.expected[-1], 'outlook_low': forecast.low[-1],
        'shortfall': forecast.first_below_zero('low'), 'daily_spend': daily,
        'upcoming': [event for event in forecast.events if event[2] < 0][:3],
        'spending_alerts': alerts[:2], 'goal_preview': goals,
        'budget_summary': budget_summary(user, today), 'category_rows': categories,
        'history_days': user.transactions.filter(date__lte=today, date__gt=today - timedelta(days=90)).count(),
    }
