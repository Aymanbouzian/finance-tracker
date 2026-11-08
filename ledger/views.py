import csv
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic

from .forms import AccountForm, CategoryForm, CSVImportForm, RegisterForm, TransactionForm
from .importer import parse_csv
from .mixins import UserFormMixin, UserQuerysetMixin
from .models import Account, Category, Transaction
from .services import (
    create_default_categories,
    expense_breakdown,
    month_bounds,
    monthly_history,
    total_balance,
    totals_between,
)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        create_default_categories(user)
        login(request, user)
        messages.success(request, "Welcome! Start by adding an account.")
        return redirect("account-list")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    today = timezone.localdate()
    accounts = [(a, a.balance) for a in Account.objects.filter(user=request.user)]
    month_start, month_end = month_bounds(today.year, today.month)
    income, expense = totals_between(request.user, month_start, month_end)
    breakdown = expense_breakdown(request.user, month_start, month_end)
    history = monthly_history(request.user, today)
    chart = {
        "categories": {"labels": [n for n, _ in breakdown], "values": [float(v) for _, v in breakdown]},
        "history": {
            "labels": [h["label"] for h in history],
            "income": [float(h["income"]) for h in history],
            "expense": [float(h["expense"]) for h in history],
        },
    }
    context = {
        "accounts": accounts,
        "total": total_balance(request.user),
        "income": income,
        "expense": expense,
        "net": income - expense,
        "month_label": today.strftime("%B %Y"),
        "chart": chart,
        "recent": request.user.transactions.select_related("account", "category", "to_account")[:8],
    }
    return render(request, "ledger/dashboard.html", context)


# ---- Accounts ---------------------------------------------------------------

class AccountList(LoginRequiredMixin, generic.ListView):
    template_name = "ledger/account_list.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total"] = sum((a.balance for a in context["accounts"]), Decimal("0.00"))
        return context


class AccountCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, generic.CreateView):
    model = Account
    form_class = AccountForm
    template_name = "form.html"
    success_url = reverse_lazy("account-list")
    success_message = "Account created."
    extra_context = {"title": "New account", "cancel_url": reverse_lazy("account-list")}


class AccountUpdate(UserQuerysetMixin, UserFormMixin, SuccessMessageMixin, generic.UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "form.html"
    success_url = reverse_lazy("account-list")
    success_message = "Account updated."
    extra_context = {"title": "Edit account", "cancel_url": reverse_lazy("account-list")}


class AccountDelete(UserQuerysetMixin, generic.DeleteView):
    model = Account
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("account-list")
    extra_context = {
        "title": "Delete account",
        "warning": "All transactions in this account, and transfers into it, will be deleted too.",
        "cancel_url": reverse_lazy("account-list"),
    }


# ---- Categories -------------------------------------------------------------

class CategoryList(LoginRequiredMixin, generic.ListView):
    template_name = "ledger/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, generic.CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "form.html"
    success_url = reverse_lazy("category-list")
    success_message = "Category created."
    extra_context = {"title": "New category", "cancel_url": reverse_lazy("category-list")}


class CategoryDelete(UserQuerysetMixin, generic.DeleteView):
    model = Category
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("category-list")
    extra_context = {
        "title": "Delete category",
        "warning": "Transactions keep existing but become uncategorized.",
        "cancel_url": reverse_lazy("category-list"),
    }


# ---- Transactions -----------------------------------------------------------

def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class TransactionList(LoginRequiredMixin, generic.ListView):
    template_name = "ledger/transaction_list.html"
    paginate_by = 25

    def get_queryset(self):
        queryset = self.request.user.transactions.select_related("account", "to_account", "category")
        params = self.request.GET
        account_id = _to_int(params.get("account"))
        if account_id:
            queryset = queryset.filter(Q(account_id=account_id) | Q(to_account_id=account_id))
        category_id = _to_int(params.get("category"))
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if params.get("kind") in {Transaction.INCOME, Transaction.EXPENSE, Transaction.TRANSFER}:
            queryset = queryset.filter(kind=params["kind"])
        if params.get("month"):
            try:
                first = datetime.strptime(params["month"], "%Y-%m").date()
            except ValueError:
                first = None
            if first:
                start, end = month_bounds(first.year, first.month)
                queryset = queryset.filter(date__gte=start, date__lte=end)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        context.update(
            accounts=Account.objects.filter(user=self.request.user),
            categories=Category.objects.filter(user=self.request.user),
            filters=self.request.GET,
            querystring=query.urlencode(),
            kinds=Transaction.KINDS,
        )
        return context


class TransactionCreate(LoginRequiredMixin, UserFormMixin, SuccessMessageMixin, generic.CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "ledger/transaction_form.html"
    success_url = reverse_lazy("transaction-list")
    success_message = "Transaction saved."
    extra_context = {"title": "Add transaction", "cancel_url": reverse_lazy("transaction-list")}


class TransactionUpdate(UserQuerysetMixin, UserFormMixin, SuccessMessageMixin, generic.UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "ledger/transaction_form.html"
    success_url = reverse_lazy("transaction-list")
    success_message = "Transaction updated."
    extra_context = {"title": "Edit transaction", "cancel_url": reverse_lazy("transaction-list")}


class TransactionDelete(UserQuerysetMixin, generic.DeleteView):
    model = Transaction
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("transaction-list")
    extra_context = {"title": "Delete transaction", "cancel_url": reverse_lazy("transaction-list")}


# ---- CSV import / export ----------------------------------------------------

@login_required
def import_csv(request):
    form = CSVImportForm(request.POST or None, request.FILES or None, user=request.user)
    errors = []
    if request.method == "POST" and form.is_valid():
        categories = {c.name.lower(): c for c in Category.objects.filter(user=request.user)}
        rows, errors = parse_csv(form.cleaned_data["file"], categories)
        if not errors and not rows:
            errors = ["The file contains no transactions."]
        if not errors:
            account = form.cleaned_data["account"]
            Transaction.objects.bulk_create(
                [Transaction(user=request.user, account=account, **row) for row in rows]
            )
            messages.success(request, f"Imported {len(rows)} transactions.")
            return redirect("transaction-list")
    return render(request, "ledger/import.html", {"form": form, "errors": errors[:20], "error_count": len(errors)})


def _safe_cell(value):
    """Neutralise spreadsheet formula injection in exported text."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@login_required
def export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(["date", "account", "kind", "amount", "category", "description", "to_account"])
    rows = request.user.transactions.select_related("account", "to_account", "category").order_by("date", "id")
    for t in rows:
        writer.writerow(
            [
                t.date.isoformat(),
                _safe_cell(t.account.name),
                t.kind,
                t.amount,
                _safe_cell(t.category.name if t.category else ""),
                _safe_cell(t.description),
                _safe_cell(t.to_account.name if t.to_account else ""),
            ]
        )
    return response
