from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, Category, Transaction

from .forms import BudgetForm
from .models import Budget
from .services import budget_summary

User = get_user_model()
D = Decimal
TODAY = date(2026, 11, 15)


class BudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("planner", password="budget-password")
        cls.other = User.objects.create_user("other", password="budget-password")
        cls.account = Account.objects.create(user=cls.user, name="Everyday")
        cls.food = Category.objects.create(user=cls.user, name="Food", kind="expense")
        cls.transport = Category.objects.create(user=cls.user, name="Transport", kind="expense")
        cls.salary = Category.objects.create(user=cls.user, name="Salary", kind="income")
        cls.foreign = Category.objects.create(user=cls.other, name="Secret category", kind="expense")

    def budget(self, category=None, amount="300.00", month=TODAY):
        return Budget.objects.create(user=self.user, category=category or self.food, amount=D(amount), month=month)

    def spend(self, amount, category=None, on=TODAY, kind="expense"):
        return Transaction.objects.create(
            user=self.user, account=self.account, category=category,
            kind=kind, amount=D(amount), date=on,
        )

    def test_month_normalization_and_duplicate_constraint(self):
        budget = self.budget()
        self.assertEqual(budget.month, date(2026, 11, 1))
        with self.assertRaises(ValidationError):
            self.budget(month=date(2026, 11, 30))
        self.budget(month=date(2026, 12, 1))
        self.assertEqual(Budget.objects.count(), 2)

    def test_budget_rejects_nonpositive_income_and_foreign_category(self):
        for kwargs in ({"amount": "0"}, {"amount": "-1"}, {"category": self.salary}, {"category": self.foreign}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.budget(**kwargs)

    def test_summary_counts_only_owned_recorded_expenses_in_selected_month(self):
        self.budget()
        self.spend("100.25", self.food)
        self.spend("999", self.food, on=date(2026, 10, 31))
        self.spend("888", self.food, on=date(2026, 11, 16))
        self.spend("777", self.food, kind="income")
        self.spend("666", self.food, kind="transfer")
        # Even a malformed record pointing to this user's category cannot leak into totals.
        other_account = Account.objects.create(user=self.other, name="Other")
        Transaction.objects.create(user=self.other, account=other_account, category=self.food, amount=D("900"), date=TODAY, kind="expense")
        Budget.objects.create(user=self.other, category=self.foreign, amount=D("10"), month=TODAY)
        summary = budget_summary(self.user, TODAY)
        self.assertEqual(summary["total_budget"], D("300"))
        self.assertEqual(summary["total_spent"], D("100.25"))
        self.assertEqual(len(summary["rows"]), 1)
        self.assertEqual(summary["rows"][0]["remaining"], D("199.75"))
        self.assertEqual(summary["rows"][0]["status"], "on-track")

    def test_over_limit_and_pacing_use_decimal_and_retain_signed_remaining(self):
        self.budget(amount="100.00")
        self.budget(self.transport, amount="200.00")
        self.spend("120.10", self.food)
        self.spend("110.00", self.transport)
        self.spend("7.50")
        summary = budget_summary(self.user, TODAY)
        food, transport = summary["rows"]
        self.assertEqual(food["used_percent"], D("120.10"))
        self.assertEqual(food["percent"], D("100"))
        self.assertEqual(food["over_amount"], D("20.10"))
        self.assertEqual(food["remaining"], D("-20.10"))
        self.assertEqual(food["status"], "over")
        self.assertEqual(transport["expected_spend"], D("100.00"))
        self.assertEqual(transport["status"], "ahead")
        self.assertEqual(summary["unbudgeted_spent"], D("7.50"))
        self.assertEqual(summary["total_remaining"], D("69.90"))
        self.assertEqual(summary["over_count"], 1)
        self.assertEqual(summary["elapsed_percent"], D("50.00"))

    def test_historical_future_and_leap_months(self):
        self.budget(month=date(2024, 2, 1), amount="290")
        self.spend("10", self.food, on=date(2024, 2, 29))
        summary = budget_summary(self.user, TODAY, date(2024, 2, 1))
        self.assertEqual(summary["days_in_month"], 29)
        self.assertEqual(summary["elapsed_days"], 29)
        self.assertEqual(summary["rows"][0]["status"], "within")
        self.budget(month=date(2027, 1, 1))
        self.spend("80", self.food, on=date(2027, 1, 2))
        summary = budget_summary(self.user, TODAY, date(2027, 1, 1))
        self.assertEqual(summary["elapsed_days"], 0)
        self.assertEqual(summary["total_spent"], D("0"))
        self.assertEqual(summary["rows"][0]["status"], "planned")

    def test_form_limits_choices_and_handles_duplicate_as_error(self):
        self.budget()
        form = BudgetForm(user=self.user)
        self.assertQuerySetEqual(form.fields["category"].queryset, [self.food, self.transport])
        for category in (self.foreign, self.salary, self.food):
            form = BudgetForm(user=self.user, data={"category": category.pk, "month": "2026-11", "amount": "100"})
            self.assertFalse(form.is_valid())
            self.assertIn("category", form.errors)
        form = BudgetForm(user=self.user, data={"category": self.transport.pk, "month": "2026-11", "amount": "12.34"})
        self.assertTrue(form.is_valid(), form.errors)
        created = form.save()
        self.assertEqual(created.user, self.user)
        self.assertEqual(created.month, date(2026, 11, 1))
        self.assertEqual(created.amount, D("12.34"))

    def test_all_views_require_login_and_enforce_ownership(self):
        budget = self.budget()
        for name, args in (("budget-list", []), ("budget-create", []), ("budget-update", [budget.pk]), ("budget-delete", [budget.pk])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302)
        self.client.force_login(self.other)
        response = self.client.get(reverse("budget-list") + "?month=2026-11")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["rows"], [])
        self.assertEqual(self.client.get(reverse("budget-update", args=[budget.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("budget-delete", args=[budget.pk])).status_code, 404)
        self.assertTrue(Budget.objects.filter(pk=budget.pk).exists())

    def test_create_update_and_delete_budget_preserve_transactions(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("budget-create"), {"category": self.food.pk, "month": "2026-11", "amount": "500"})
        self.assertRedirects(response, reverse("budget-list") + "?month=2026-11")
        budget = Budget.objects.get(user=self.user)
        response = self.client.post(reverse("budget-update", args=[budget.pk]), {"category": self.food.pk, "month": "2026-11", "amount": "650.25"})
        self.assertEqual(response.status_code, 302)
        budget.refresh_from_db()
        self.assertEqual(budget.amount, D("650.25"))
        tx = self.spend("25", self.food)
        response = self.client.post(reverse("budget-delete", args=[budget.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Budget.objects.filter(pk=budget.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=tx.pk).exists())

    def test_invalid_month_filter_does_not_crash(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("budget-list") + "?month=not-a-month").status_code, 200)
