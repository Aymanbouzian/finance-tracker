from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic

from ledger.dates import add_months
from ledger.mixins import UserFormMixin, UserQuerysetMixin
from ledger.services import total_balance

from .forecast import EXPENSE, INCOME, MONTHLY, OneOff, Recurring, build_forecast, q, required_monthly
from .forms import ForecastForm, RecurringItemForm, SavingsGoalForm, WhatIfForm
from .models import RecurringItem, SavingsGoal
from .services import estimate_daily_spend, estimate_monthly_surplus, recurring_items


def _series(forecast, *names):
    return {
        "labels": [d.isoformat() for d in forecast.dates],
        **{name: [float(v) for v in getattr(forecast, name)] for name in names},
    }


@login_required
def forecast_view(request):
    today = timezone.localdate()
    form = ForecastForm(request.GET or None)
    days, override = 90, None
    if form.is_bound and form.is_valid():
        days = form.cleaned_data["days"]
        override = form.cleaned_data["daily_spend"]

    estimated = estimate_daily_spend(request.user, today)
    daily = override if override is not None else estimated
    start_balance = total_balance(request.user)
    result = build_forecast(start_balance, today, days, recurring_items(request.user), daily)
    low_date, low_value = result.min_point("expected")
    context = {
        "form": form,
        "days": days,
        "estimated": estimated,
        "daily": q(daily),
        "start_balance": q(start_balance),
        "end_expected": result.expected[-1],
        "end_low": result.low[-1],
        "end_high": result.high[-1],
        "lowest_date": low_date,
        "lowest_value": low_value,
        "shortfall_expected": result.first_below_zero("expected"),
        "shortfall_low": result.first_below_zero("low"),
        "events": result.events[:20],
        "chart": _series(result, "expected", "low", "high"),
    }
    return render(request, "planning/forecast.html", context)


@login_required
def what_if_view(request):
    today = timezone.localdate()
    form = WhatIfForm(request.GET or None)
    context = {"form": form}
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        days = data["days"]
        base_daily = estimate_daily_spend(request.user, today)
        start_balance = total_balance(request.user)
        items = recurring_items(request.user)

        one_offs = []
        if data["purchase_amount"]:
            one_offs.append(OneOff("Planned purchase", -data["purchase_amount"], data["purchase_date"]))

        scenario_items = list(items)
        change = data["monthly_income_change"]
        if change:
            kind = INCOME if change > 0 else EXPENSE
            label = "Income increase" if change > 0 else "Income loss"
            scenario_items.append(Recurring(label, kind, abs(change), MONTHLY, add_months(today, 1)))

        cut = data["monthly_expense_cut"] or Decimal(0)
        scenario_daily = max(base_daily - cut * 12 / 365, Decimal(0))

        baseline = build_forecast(start_balance, today, days, items, base_daily)
        scenario = build_forecast(start_balance, today, days, scenario_items, scenario_daily, one_offs)
        context["result"] = {
            "baseline_end": baseline.expected[-1],
            "scenario_end": scenario.expected[-1],
            "difference": scenario.expected[-1] - baseline.expected[-1],
            "scenario_end_low": scenario.low[-1],
            "baseline_min": baseline.min_point("expected"),
            "scenario_min": scenario.min_point("expected"),
            "baseline_shortfall": baseline.first_below_zero("expected"),
            "scenario_shortfall": scenario.first_below_zero("expected"),
            "scenario_shortfall_low": scenario.first_below_zero("low"),
            "chart": {
                "labels": [d.isoformat() for d in baseline.dates],
                "baseline": [float(v) for v in baseline.expected],
                "scenario": [float(v) for v in scenario.expected],
            },
        }
    return render(request, "planning/whatif.html", context)


@login_required
def goal_list(request):
    today = timezone.localdate()
    rows, total_required = [], Decimal("0.00")
    for goal in SavingsGoal.objects.filter(user=request.user):
        monthly = required_monthly(goal.remaining, today, goal.target_date)
        if monthly:
            total_required += monthly
        percent = min(int(goal.saved_so_far / goal.target_amount * 100), 100)
        rows.append({"goal": goal, "monthly": monthly, "percent": percent})
    surplus = estimate_monthly_surplus(request.user, today)
    return render(
        request,
        "planning/goals.html",
        {
            "rows": rows,
            "total_required": total_required,
            "surplus": surplus,
            "gap": q(total_required - surplus),
            "affordable": total_required <= surplus,
        },
    )


class GoalCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, generic.CreateView):
    model = SavingsGoal
    form_class = SavingsGoalForm
    template_name = "form.html"
    success_url = reverse_lazy("goal-list")
    success_message = "Goal created."
    extra_context = {"title": "New savings goal", "cancel_url": reverse_lazy("goal-list")}


class GoalUpdate(UserQuerysetMixin, UserFormMixin, SuccessMessageMixin, generic.UpdateView):
    model = SavingsGoal
    form_class = SavingsGoalForm
    template_name = "form.html"
    success_url = reverse_lazy("goal-list")
    success_message = "Goal updated."
    extra_context = {"title": "Edit savings goal", "cancel_url": reverse_lazy("goal-list")}


class GoalDelete(UserQuerysetMixin, generic.DeleteView):
    model = SavingsGoal
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("goal-list")
    extra_context = {"title": "Delete goal", "cancel_url": reverse_lazy("goal-list")}


class RecurringList(LoginRequiredMixin, generic.ListView):
    template_name = "planning/recurring_list.html"
    context_object_name = "items"

    def get_queryset(self):
        return RecurringItem.objects.filter(user=self.request.user)


class RecurringCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, generic.CreateView):
    model = RecurringItem
    form_class = RecurringItemForm
    template_name = "form.html"
    success_url = reverse_lazy("recurring-list")
    success_message = "Recurring item saved."

    def get_initial(self):
        return {"next_date": timezone.localdate() + timedelta(days=1)}

    extra_context = {"title": "New recurring income or bill", "cancel_url": reverse_lazy("recurring-list")}


class RecurringUpdate(UserQuerysetMixin, UserFormMixin, SuccessMessageMixin, generic.UpdateView):
    model = RecurringItem
    form_class = RecurringItemForm
    template_name = "form.html"
    success_url = reverse_lazy("recurring-list")
    success_message = "Recurring item updated."
    extra_context = {"title": "Edit recurring item", "cancel_url": reverse_lazy("recurring-list")}


class RecurringDelete(UserQuerysetMixin, generic.DeleteView):
    model = RecurringItem
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("recurring-list")
    extra_context = {"title": "Delete recurring item", "cancel_url": reverse_lazy("recurring-list")}
