"""Session-authenticated JSON API for the Flutter clients; no financial math in UI."""

import csv
import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.views.csrf import csrf_failure as html_csrf_failure

from assistant.forms import AssistantForm
from assistant.services import AssistantUnavailable, ask_assistant, configuration, connection_status, financial_summary
from budgets.forms import BudgetForm
from budgets.models import Budget
from ledger.dates import add_months
from ledger.forms import AccountForm, CategoryForm, CSVImportForm, RegisterForm, StyledAuthenticationForm, TransactionForm
from ledger.importer import parse_csv
from ledger.insights import dashboard_insights
from ledger.models import Account, Category, Transaction
from ledger.services import create_default_categories, expense_breakdown, month_bounds, monthly_history, total_balance, totals_between
from ledger.views import export_csv
from planning.forecast import EXPENSE, INCOME, MONTHLY, OneOff, Recurring, build_forecast
from planning.forms import ForecastForm, RecurringItemForm, SavingsGoalForm, WhatIfForm
from planning.models import RecurringItem, SavingsGoal
from planning.services import estimate_daily_spend, recurring_items

from .serializers import budget_snapshot, event_record, forecast_record, iso, money, record

MAX_JSON_BYTES = 64 * 1024
LOGIN_WINDOW = 600
LOGIN_LIMIT = 10
LOGIN_IP_LIMIT = 50
RESOURCES = {
    "transactions": (Transaction, TransactionForm), "accounts": (Account, AccountForm),
    "categories": (Category, CategoryForm), "budgets": (Budget, BudgetForm),
    "goals": (SavingsGoal, SavingsGoalForm), "recurring": (RecurringItem, RecurringItemForm),
}


class ApiError(Exception):
    def __init__(self, message, code="bad_request", status=400, errors=None):
        self.message, self.code, self.status, self.errors = message, code, status, errors


def error_response(message, code, status, errors=None):
    body = {"error": message, "code": code}
    if errors is not None:
        body["errors"] = errors
    return JsonResponse(body, status=status)


def api(methods=("GET",), authenticated=True):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                if request.method not in methods:
                    response = error_response("This request method is not supported.", "method_not_allowed", 405)
                    response["Allow"] = ", ".join(methods)
                elif authenticated and not request.user.is_authenticated:
                    response = error_response("Sign in to continue.", "unauthenticated", 401)
                else:
                    response = view(request, *args, **kwargs)
            except ApiError as error:
                response = error_response(error.message, error.code, error.status, error.errors)
            except Http404:
                response = error_response("The requested record was not found.", "not_found", 404)
            except ValidationError as error:
                errors = error.message_dict if hasattr(error, "message_dict") else {"__all__": error.messages}
                response = error_response("Check the highlighted fields.", "validation_error", 400, errors)
            except IntegrityError:
                response = error_response("A matching record already exists. Refresh and try again.", "conflict", 409)
            except RequestDataTooBig:
                response = error_response("The request is too large.", "request_too_large", 413)
            patch_cache_control(response, private=True, no_store=True, no_cache=True, max_age=0)
            return response
        return wrapped
    return decorate


def payload(request):
    if request.content_type != "application/json":
        raise ApiError("Send a JSON object with Content-Type: application/json.", "unsupported_media_type", 415)
    if len(request.body) > MAX_JSON_BYTES:
        raise ApiError("The request is too large.", "request_too_large", 413)
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise ApiError("The request body is not valid JSON.", "invalid_json") from None
    if not isinstance(data, dict) or any(not isinstance(key, str) or isinstance(value, (dict, list)) for key, value in data.items()):
        raise ApiError("Send an object containing simple field values.", "invalid_json")
    return data


def validate(form):
    if not form.is_valid():
        raise ApiError("Check the highlighted fields.", "validation_error", errors={field: list(messages) for field, messages in form.errors.items()})
    return form


def session_body(request):
    user = request.user
    return {
        "authenticated": user.is_authenticated,
        "user": {"username": user.username, "first_name": user.first_name} if user.is_authenticated else None,
        "csrfToken": get_token(request), "currency": settings.CURRENCY,
    }


@api(authenticated=False)
def session(request):
    return JsonResponse(session_body(request))


def attempt_keys(request, username):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    # Ignore untrusted X-Forwarded-For. Use a shared cache with multiple workers.
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    return "clientapi-login-" + digest(ip + ":" + username.casefold()), "clientapi-login-ip-" + digest(ip)


def record_attempt(key):
    if not cache.add(key, 1, timeout=LOGIN_WINDOW):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=LOGIN_WINDOW)


@api(("POST",), authenticated=False)
def login_view(request):
    data = payload(request)
    username = str(data.get("username") or "")[:150]
    account_key, ip_key = attempt_keys(request, username)
    if cache.get(account_key, 0) >= LOGIN_LIMIT or cache.get(ip_key, 0) >= LOGIN_IP_LIMIT:
        response = error_response("Too many sign-in attempts. Try again in 10 minutes.", "rate_limited", 429)
        response["Retry-After"] = str(LOGIN_WINDOW)
        return response
    form = StyledAuthenticationForm(request=request, data=data)
    if not form.is_valid():
        record_attempt(account_key)
        record_attempt(ip_key)
        return error_response("The username or password is incorrect.", "invalid_credentials", 401)
    cache.delete(account_key)
    login(request, form.get_user())
    return JsonResponse(session_body(request))


@api(("POST",), authenticated=False)
def register(request):
    data = payload(request)
    first_name = str(data.get("first_name") or "").strip()
    if len(first_name) > 150:
        raise ApiError("Check the highlighted fields.", "validation_error", errors={"first_name": ["Use 150 characters or fewer."]})
    form = validate(RegisterForm(data=data))
    with transaction.atomic():
        user = form.save(commit=False)
        user.first_name = first_name
        user.save()
        create_default_categories(user)
    login(request, user)
    return JsonResponse(session_body(request), status=201)


@api(("POST",))
def logout_view(request):
    payload(request)
    logout(request)
    rotate_token(request)
    return JsonResponse(session_body(request))


def csrf_failure(request, reason=""):
    if not request.path.startswith("/api/"):
        return html_csrf_failure(request, reason=reason)
    response = error_response("Your session verification expired. Refresh your session and try again.", "csrf_failed", 403)
    patch_cache_control(response, private=True, no_store=True, no_cache=True, max_age=0)
    return response


def parse_month(value):
    if not value:
        return timezone.localdate().replace(day=1)
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except (TypeError, ValueError):
        raise ApiError("Use a month in YYYY-MM format.", "validation_error", errors={"month": ["Use YYYY-MM."]}) from None


def owned_queryset(request, resource):
    if resource not in RESOURCES:
        raise Http404
    model, _ = RESOURCES[resource]
    queryset = model.objects.filter(user=request.user)
    if resource == "transactions":
        queryset = queryset.select_related("account", "to_account", "category")
        search = request.GET.get("q", "").strip()[:200]
        if search:
            queryset = queryset.filter(Q(description__icontains=search) | Q(category__name__icontains=search) | Q(account__name__icontains=search))
        for field in ("account", "category"):
            value = request.GET.get(field)
            if value:
                try:
                    key = int(value)
                except ValueError:
                    raise ApiError("Use a valid record ID.", "validation_error", errors={field: ["Use an integer ID."]}) from None
                queryset = queryset.filter(Q(account_id=key) | Q(to_account_id=key)) if field == "account" else queryset.filter(category_id=key)
        if request.GET.get("kind"):
            if request.GET["kind"] not in {"income", "expense", "transfer"}:
                raise ApiError("Choose a valid transaction type.", "validation_error", errors={"kind": ["Choose income, expense, or transfer."]})
            queryset = queryset.filter(kind=request.GET["kind"])
        if request.GET.get("month"):
            month = parse_month(request.GET["month"])
            start, end = month_bounds(month.year, month.month)
            queryset = queryset.filter(date__range=(start, end))
    elif resource == "budgets":
        queryset = queryset.select_related("category")
    return queryset


def page_records(request, values):
    try:
        page_number = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 100))
        if page_number < 1 or not 1 <= page_size <= 200:
            raise ValueError
    except ValueError:
        raise ApiError("Use a positive page and a page_size from 1 to 200.", "invalid_pagination") from None
    paginator = Paginator(values, page_size)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        raise ApiError("This page does not exist.", "not_found", 404) from None
    return {"results": list(page.object_list), "count": paginator.count, "page": page.number, "pages": paginator.num_pages}


@api(("GET", "POST"))
def collection(request, resource):
    queryset = owned_queryset(request, resource)
    if request.method == "GET":
        if resource == "budgets":
            summary = budget_snapshot(request.user, timezone.localdate(), parse_month(request.GET.get("month")))
            return JsonResponse({**page_records(request, summary["rows"]), "summary": summary})
        page = page_records(request, queryset)
        page["results"] = [record(item) for item in page["results"]]
        return JsonResponse(page)
    data = payload(request)
    form_class = RESOURCES[resource][1]
    form = validate(form_class(data=data, user=request.user))
    with transaction.atomic():
        item = form.save()
    return JsonResponse({"item": record(item)}, status=201)


@api(("GET", "POST", "DELETE"))
def detail(request, resource, pk):
    # Detail lookup must not depend on list filters.
    if resource not in RESOURCES:
        raise Http404
    model, form_class = RESOURCES[resource]
    item = get_object_or_404(model, user=request.user, pk=pk)
    if request.method == "GET":
        return JsonResponse({"item": record(item)})
    if request.method == "DELETE":
        item.delete()
        return JsonResponse({"deleted": True})
    data = payload(request)
    if isinstance(item, Category) and data.get("kind") != item.kind and (item.transactions.exists() or item.budgets.exists()):
        raise ApiError("Check the highlighted fields.", "validation_error", errors={"kind": ["A category's type cannot change while transactions or budgets use it."]})
    form = validate(form_class(data=data, instance=item, user=request.user))
    with transaction.atomic():
        item = form.save()
    return JsonResponse({"item": record(item)})


def make_forecast(user, days=90, daily_override=None):
    today = timezone.localdate()
    estimated = estimate_daily_spend(user, today)
    daily = daily_override if daily_override is not None else estimated
    result = build_forecast(total_balance(user), today, days, recurring_items(user), daily)
    return result, daily, estimated


@api()
def forecast(request):
    data = request.GET.copy()
    data.setdefault("days", 90)
    form = validate(ForecastForm(data))
    result, daily, estimated = make_forecast(request.user, form.cleaned_data["days"], form.cleaned_data["daily_spend"])
    return JsonResponse(forecast_record(result, daily, estimated))


@api()
def overview(request):
    user, today = request.user, timezone.localdate()
    start, _ = month_bounds(today.year, today.month)
    income, expense = totals_between(user, start, today)
    breakdown = expense_breakdown(user, start, today)
    insights = dashboard_insights(user, today, breakdown)
    result, daily, estimated = make_forecast(user, 30)
    return JsonResponse({
        "as_of": iso(today), "currency": settings.CURRENCY, "month_label": today.strftime("%B %Y"),
        "balance": money(total_balance(user)), "income": money(income), "expense": money(expense),
        "net": money(income - expense), "savings_rate": money((income - expense) / income * 100 if income else 0),
        "accounts": [record(item) for item in Account.objects.filter(user=user)],
        "recent": [record(item) for item in Transaction.objects.filter(user=user, date__lte=today).select_related("account", "to_account", "category")[:8]],
        "history": [{"label": row["label"], "income": money(row["income"]), "expense": money(row["expense"])} for row in monthly_history(user, today)],
        "spending": [{**row, "amount": money(row["amount"]), "percent": money(row["percent"])} for row in insights["category_rows"]],
        "budgets": budget_snapshot(user, today),
        "goals": [record(item, today) for item in SavingsGoal.objects.filter(user=user)],
        "recurring": [record(item, today) for item in RecurringItem.objects.filter(user=user)],
        "upcoming": [event_record(event) for event in result.events if event[2] < 0][:8],
        "forecast": forecast_record(result, daily, estimated),
        "insights": [{**row, "change": money(row["change"])} for row in insights["spending_alerts"]],
    })


@api(("POST",))
def what_if(request):
    data = payload(request)
    data.setdefault("days", 90)
    form = validate(WhatIfForm(data))
    data = form.cleaned_data
    today = timezone.localdate()
    daily = estimate_daily_spend(request.user, today)
    balance = total_balance(request.user)
    items = recurring_items(request.user)
    scenario_items = list(items)
    one_offs = []
    if data["purchase_amount"]:
        one_offs.append(OneOff("Planned purchase", -data["purchase_amount"], data["purchase_date"]))
    change = data["monthly_income_change"]
    if change:
        scenario_items.append(Recurring("Income increase" if change > 0 else "Income loss", INCOME if change > 0 else EXPENSE, abs(change), MONTHLY, add_months(today, 1)))
    cut = data["monthly_expense_cut"] or Decimal(0)
    scenario_daily = max(daily - cut * 12 / 365, Decimal(0))
    baseline = build_forecast(balance, today, data["days"], items, daily)
    scenario = build_forecast(balance, today, data["days"], scenario_items, scenario_daily, one_offs)
    base_day, base_amount = baseline.min_point()
    scenario_day, scenario_amount = scenario.min_point()
    return JsonResponse({
        "baseline_end": money(baseline.expected[-1]), "scenario_end": money(scenario.expected[-1]),
        "difference": money(scenario.expected[-1] - baseline.expected[-1]), "scenario_end_low": money(scenario.low[-1]),
        "baseline_min": {"date": iso(base_day), "amount": money(base_amount)},
        "scenario_min": {"date": iso(scenario_day), "amount": money(scenario_amount)},
        "baseline_shortfall": iso(baseline.first_below_zero()), "scenario_shortfall": iso(scenario.first_below_zero()),
        "scenario_shortfall_low": iso(scenario.first_below_zero("low")),
        "dates": [iso(day) for day in baseline.dates],
        "baseline": [money(value) for value in baseline.expected], "scenario": [money(value) for value in scenario.expected],
    })


@api(("GET", "POST"))
def assistant(request):
    summary = financial_summary(request.user)
    config = configuration()
    if request.method == "GET":
        return JsonResponse({"summary": summary, "status": connection_status(), "enabled": config["enabled"], "model": config["model"]})
    data = payload(request)
    if data.get("share_summary") is not True:
        raise ApiError("Approve sharing the displayed summary before asking.", "validation_error", errors={"share_summary": ["Explicit approval is required for each question."]})
    form = validate(AssistantForm(data))
    try:
        answer = ask_assistant(form.cleaned_data["question"], summary)
    except AssistantUnavailable as error:
        raise ApiError(str(error), "assistant_unavailable", 503) from None
    return JsonResponse({"answer": answer, "summary": summary, "model": config["model"]})


@api()
def export(request):
    return export_csv(request)


@api(("POST",))
def import_file(request):
    form = validate(CSVImportForm(request.POST, request.FILES, user=request.user))
    # Exports use positive amounts plus a kind column; bank statements use
    # signed amounts. Never silently turn an exported expense into income.
    try:
        headers = next(csv.reader(io.StringIO(form.cleaned_data["file"]), strict=True), [])
    except csv.Error:
        headers = []  # The shared parser returns the detailed CSV error below.
    if any(header.strip().lower() == "kind" for header in headers):
        raise ApiError("Use a bank-statement CSV with signed amounts. Ledger exports are not an import template.", "validation_error", errors={"file": ["Remove the kind column and use negative amounts for expenses and positive amounts for income. Record transfers in the ledger."]})
    categories = {item.name.lower(): item for item in Category.objects.filter(user=request.user)}
    rows, errors = parse_csv(form.cleaned_data["file"], categories)
    if errors or not rows:
        raise ApiError("The CSV was not imported. Check its rows and try again.", "validation_error", errors={"file": errors[:20] or ["The file contains no transactions."]})
    with transaction.atomic():
        Transaction.objects.bulk_create([Transaction(user=request.user, account=form.cleaned_data["account"], **row) for row in rows])
    return JsonResponse({"imported": len(rows)}, status=201)


@api(authenticated=False)
def not_found(request, **kwargs):
    raise Http404
