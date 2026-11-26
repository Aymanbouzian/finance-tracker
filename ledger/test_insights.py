from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from budgets.models import Budget
from planning.models import RecurringItem, SavingsGoal

from .insights import dashboard_insights
from .models import Account, Category, Transaction
from .services import expense_breakdown, total_balance

D = Decimal
TODAY = date(2026, 11, 14)


class DashboardInsightTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("insights-owner", password="insight-password")
        cls.other = get_user_model().objects.create_user("insights-other", password="insight-password")
        cls.checking = Account.objects.create(user=cls.user, name="Checking", opening_balance=D("1000"))
        cls.savings = Account.objects.create(user=cls.user, name="Savings", opening_balance=D("200"))
        cls.foreign_account = Account.objects.create(user=cls.other, name="Private account", opening_balance=D("99999"))
        cls.food = Category.objects.create(user=cls.user, name="Food", kind="expense")
        cls.foreign_food = Category.objects.create(user=cls.other, name="Food", kind="expense")

    def setUp(self):
        clock = patch("django.utils.timezone.localdate", return_value=TODAY)
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.client.force_login(self.user)

    def record(self, kind, amount, on=TODAY, account=None, category=None, to_account=None, description=""):
        account = account or self.checking
        # Direct creation also represents legacy future rows, which remain in storage.
        return Transaction.objects.create(
            user=account.user, account=account, kind=kind, amount=D(amount), date=on,
            category=category, to_account=to_account, description=description,
        )

    def insights(self, today=TODAY):
        breakdown = expense_breakdown(self.user, today.replace(day=1), today)
        return dashboard_insights(self.user, today, breakdown)

    def test_current_balances_ignore_future_income_expenses_and_both_transfer_directions(self):
        self.record("income", "500")
        self.record("expense", "100")
        self.record("transfer", "150", to_account=self.savings)
        self.record("income", "50", account=self.savings)
        self.record("expense", "20", account=self.savings)
        self.record("transfer", "25", account=self.savings, to_account=self.checking)
        future = TODAY + timedelta(days=1)
        self.record("income", "999", on=future)
        self.record("expense", "888", on=future)
        self.record("transfer", "777", on=future, to_account=self.savings)
        self.record("income", "666", on=future, account=self.savings)
        self.record("expense", "555", on=future, account=self.savings)
        self.record("transfer", "444", on=future, account=self.savings, to_account=self.checking)
        self.assertEqual(self.checking.balance, D("1275"))
        self.assertEqual(self.savings.balance, D("355"))
        self.assertEqual(total_balance(self.user), D("1630"))
        self.assertEqual(Transaction.objects.filter(user=self.user, date=future).count(), 6)

    def test_dashboard_month_to_date_cards_category_chart_and_history_agree(self):
        self.record("income", "2000")
        self.record("expense", "120.25", category=self.food)
        self.record("expense", "30.50")
        self.record("transfer", "400", to_account=self.savings)
        self.record("income", "900", on=date(2026, 10, 30))
        self.record("expense", "80", on=date(2026, 10, 30), category=self.food)
        self.record("income", "800", on=date(2026, 9, 30))
        self.record("expense", "60", on=date(2026, 9, 30))
        self.record("income", "999", on=date(2026, 11, 15))
        self.record("expense", "500", on=date(2026, 11, 15), category=self.food, description="future-private-marker")
        self.record("transfer", "300", on=date(2026, 11, 15), to_account=self.savings)
        self.record("expense", "700", on=date(2026, 12, 1))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context["income"], D("2000"))
        self.assertEqual(context["expense"], D("150.75"))
        self.assertEqual(context["net"], D("1849.25"))
        self.assertEqual(context["total"], D("4609.25"))
        self.assertEqual(context["history_rows"][-1]["income"], context["income"])
        self.assertEqual(context["history_rows"][-1]["expense"], context["expense"])
        self.assertEqual(context["chart"]["history"]["income"][-1], float(context["income"]))
        self.assertEqual(context["chart"]["history"]["expense"][-1], float(context["expense"]))
        self.assertEqual(context["chart"]["categories"], {"labels": ["Food", "Uncategorized"], "values": [120.25, 30.5]})
        self.assertEqual(sum(row["amount"] for row in context["category_rows"]), context["expense"])
        self.assertEqual(context["history_rows"][-2]["income"], D("900"))
        self.assertEqual(context["history_rows"][-2]["expense"], D("80"))
        self.assertTrue(all(item.date <= TODAY for item in context["recent"]))
        self.assertNotContains(response, "future-private-marker")

    def test_dashboard_insights_do_not_include_another_users_records(self):
        self.record("expense", "10000", account=self.foreign_account, category=self.foreign_food, description="other-user-secret")
        self.record("income", "15000", account=self.foreign_account)
        Budget.objects.create(user=self.other, category=self.foreign_food, month=TODAY, amount=D("20000"))
        SavingsGoal.objects.create(user=self.other, name="Private goal", target_amount=D("500"), saved_so_far=D("100"), target_date=date(2027, 1, 1))
        RecurringItem.objects.create(user=self.other, name="Private bill", kind="expense", amount=D("900"), next_date=TODAY + timedelta(days=1))
        response = self.client.get(reverse("dashboard"))
        context = response.context
        self.assertEqual(context["total"], D("1200"))
        self.assertEqual(context["income"], D("0"))
        self.assertEqual(context["expense"], D("0"))
        self.assertEqual(context["outlook"], D("1200"))
        self.assertEqual(context["outlook_low"], D("1200"))
        self.assertEqual(context["category_rows"], [])
        self.assertEqual(context["spending_alerts"], [])
        self.assertEqual(context["goal_preview"], [])
        self.assertEqual(context["upcoming"], [])
        self.assertEqual(context["budget_summary"]["rows"], [])
        self.assertEqual(list(context["recent"]), [])
        self.assertEqual({account.pk for account, _ in context["accounts"]}, {self.checking.pk, self.savings.pk})
        for marker in ("other-user-secret", "Private account", "Private goal", "Private bill"):
            self.assertNotContains(response, marker)

    def test_spending_alerts_use_same_elapsed_period_and_both_materiality_thresholds(self):
        # Only October 1–14 is the baseline for November 1–14. A large later bill
        # must not hide the increase; a legacy future entry must not create one.
        self.record("expense", "100", on=date(2026, 10, 14), category=self.food)
        self.record("expense", "9999", on=date(2026, 10, 15), category=self.food)
        self.record("expense", "250", category=self.food)
        self.record("expense", "8888", on=date(2026, 11, 15), category=self.food)
        cases = [
            ("Small absolute change", "10", "109.99"),  # below the 100 currency-unit threshold
            ("Exactly 25 percent", "400", "500"),      # percentage must exceed 25%
            ("Exactly 100 extra", "300", "400"),       # equality is allowed for the absolute threshold
            ("No baseline", None, "600"),
            ("Spending fell", "1000", "800"),
        ]
        for name, baseline, current in cases:
            category = Category.objects.create(user=self.user, name=name, kind="expense")
            if baseline:
                self.record("expense", baseline, on=date(2026, 10, 14), category=category)
            self.record("expense", current, category=category)
        # Matching category names belonging to another user must not contaminate
        # either the baseline or the current month's observations.
        self.record("expense", "50000", on=date(2026, 10, 14), account=self.foreign_account, category=self.foreign_food)
        self.record("expense", "100000", account=self.foreign_account, category=self.foreign_food)
        result = self.insights()
        alerts = {row["category"]: row for row in result["spending_alerts"]}
        self.assertEqual(set(alerts), {"Food", "Exactly 100 extra"})
        self.assertEqual(alerts["Food"], {"category": "Food", "change": D("150.00"), "percent": 150})
        self.assertEqual(alerts["Exactly 100 extra"]["change"], D("100.00"))
        self.assertEqual(alerts["Exactly 100 extra"]["percent"], 33)

    def test_spending_alerts_handle_shorter_previous_month(self):
        today = date(2026, 3, 31)
        self.clock.return_value = today
        self.record("expense", "100", on=date(2026, 2, 28), category=self.food)
        self.record("expense", "250", on=today, category=self.food)
        self.record("expense", "9999", on=date(2026, 1, 31), category=self.food)
        self.assertEqual(self.insights(today)["spending_alerts"], [{"category": "Food", "change": D("150.00"), "percent": 150}])

    def test_uncategorized_display_label_merges_explicit_and_missing_categories(self):
        named = Category.objects.create(user=self.user, name="Uncategorized", kind="expense")
        self.record("expense", "100", on=date(2026, 10, 14))
        self.record("expense", "200", on=date(2026, 10, 14), category=named)
        self.record("expense", "300", on=date(2026, 10, 14), category=self.food)
        self.record("expense", "250")
        self.record("expense", "200", category=named)
        self.record("expense", "350", category=self.food)
        self.assertEqual(
            expense_breakdown(self.user, date(2026, 10, 1), date(2026, 10, 14)),
            [("Food", D("300")), ("Uncategorized", D("300"))],
        )
        # Neither uncategorized subgroup exceeds Food alone; their combined
        # displayed total does, so sorting must happen after coalescing.
        self.assertEqual(
            expense_breakdown(self.user, TODAY.replace(day=1), TODAY),
            [("Uncategorized", D("450")), ("Food", D("350"))],
        )
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["expense"], D("800"))
        self.assertEqual(response.context["chart"]["categories"], {"labels": ["Uncategorized", "Food"], "values": [450.0, 350.0]})
        self.assertEqual(response.context["spending_alerts"], [{"category": "Uncategorized", "change": D("150.00"), "percent": 50}])
        self.assertEqual(Transaction.objects.filter(user=self.user, category=named).count(), 2)
        self.assertEqual(Transaction.objects.filter(user=self.user, category__isnull=True).count(), 2)

    def test_spending_alerts_handle_previous_calendar_year(self):
        today = date(2027, 1, 14)
        self.clock.return_value = today
        self.record("expense", "100", on=date(2026, 12, 14), category=self.food)
        self.record("expense", "9999", on=date(2026, 12, 15), category=self.food)
        self.record("expense", "250", on=today, category=self.food)
        self.assertEqual(self.insights(today)["spending_alerts"], [{"category": "Food", "change": D("150.00"), "percent": 150}])
