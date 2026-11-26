from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic

from ledger.mixins import UserFormMixin, UserQuerysetMixin

from .forms import BudgetForm, parse_month
from .models import Budget
from .services import budget_summary


@login_required
def budget_list(request):
    today = timezone.localdate()
    month = parse_month(request.GET.get("month"), today)
    summary = budget_summary(request.user, today, month)
    return render(request, "budgets/list.html", {"summary": summary, "selected_month": month.strftime("%Y-%m")})


class BudgetFormView:
    model = Budget
    form_class = BudgetForm
    template_name = "form.html"

    def get_success_url(self):
        return f"{reverse('budget-list')}?month={self.object.month:%Y-%m}"


class BudgetCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, BudgetFormView, generic.CreateView):
    success_message = "Budget created. Your expenses will update it automatically."
    extra_context = {"title": "Set a monthly budget", "cancel_url": reverse_lazy("budget-list")}

    def get_initial(self):
        return {**super().get_initial(), "month": parse_month(self.request.GET.get("month"), timezone.localdate())}


class BudgetUpdate(UserQuerysetMixin, UserFormMixin, SuccessMessageMixin, BudgetFormView, generic.UpdateView):
    success_message = "Budget updated."
    extra_context = {"title": "Edit monthly budget", "cancel_url": reverse_lazy("budget-list")}


class BudgetDelete(UserQuerysetMixin, generic.DeleteView):
    model = Budget
    template_name = "confirm_delete.html"
    extra_context = {
        "title": "Delete budget", "warning": "Your recorded transactions will be kept.",
        "cancel_url": reverse_lazy("budget-list"),
    }

    def get_success_url(self):
        return f"{reverse('budget-list')}?month={self.object.month:%Y-%m}"
