from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ledger.models import Account, Transaction

from .forecast import OneOff, Recurring, build_forecast, occurrences, required_monthly
from .models import RecurringItem, SavingsGoal
from .services import estimate_daily_spend

User = get_user_model()
D = Decimal
START = date(2026, 11, 1)


class OccurrenceTests(SimpleTestCase):
    def test_monthly_clamps_to_month_end(self):
        item = Recurring("Rent", "expense", D("100"), "monthly", date(2026, 1, 31))
        self.assertEqual(
            occurrences(item, date(2026, 1, 1), date(2026, 4, 30)),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)],
        )

    def test_weekly(self):
        item = Recurring("Gym", "expense", D("10"), "weekly", date(2026, 11, 2))
        self.assertEqual(
            occurrences(item, date(2026, 11, 1), date(2026, 11, 20)),
            [date(2026, 11, 2), date(2026, 11, 9), date(2026, 11, 16)],
        )

    def test_end_date_is_respected(self):
        item = Recurring("Loan", "expense", D("10"), "monthly", date(2026, 1, 5), end_date=date(2026, 3, 5))
        self.assertEqual(len(occurrences(item, date(2026, 1, 1), date(2026, 12, 31))), 3)

    def test_stale_next_date_still_projects_forward(self):
        item = Recurring("Rent", "expense", D("100"), "monthly", date(2025, 1, 5))
        self.assertEqual(
            occurrences(item, date(2026, 11, 2), date(2026, 12, 31)), [date(2026, 11, 5), date(2026, 12, 5)]
        )


class ForecastTests(SimpleTestCase):
    def test_everyday_spending_and_range(self):
        result = build_forecast(D("1000"), START, 10, daily_spend=D("10"))
        self.assertEqual(len(result.dates), 11)
        self.assertEqual(result.expected[-1], D("900.00"))
        self.assertEqual(result.low[-1], D("875.00"))
        self.assertEqual(result.high[-1], D("925.00"))

    def test_recurring_bill_hits_on_its_day(self):
        bill = Recurring("Rent", "expense", D("400"), "monthly", date(2026, 11, 5))
        result = build_forecast(D("1000"), START, 10, [bill])
        self.assertEqual(result.expected[3], D("1000.00"))
        self.assertEqual(result.expected[4], D("600.00"))
        self.assertEqual(result.events, [(date(2026, 11, 5), "Rent", D("-400.00"))])

    def test_event_dated_today_is_not_applied(self):
        pay = Recurring("Salary", "income", D("500"), "monthly", START)
        result = build_forecast(D("100"), START, 10, [pay])
        self.assertEqual(result.expected[-1], D("100.00"))

    def test_income_adds(self):
        pay = Recurring("Salary", "income", D("500"), "monthly", date(2026, 11, 3))
        result = build_forecast(D("100"), START, 5, [pay])
        self.assertEqual(result.expected[-1], D("600.00"))

    def test_shortfall_dates(self):
        result = build_forecast(D("100"), START, 10, daily_spend=D("20"))
        self.assertEqual(result.first_below_zero("expected"), START + timedelta(days=6))
        self.assertEqual(result.first_below_zero("low"), START + timedelta(days=5))
        self.assertIsNone(build_forecast(D("1000"), START, 10).first_below_zero("low"))

    def test_one_off_dated_today_applies_on_first_day(self):
        result = build_forecast(D("1000"), START, 3, one_offs=[OneOff("Laptop", D("-600"), START)])
        self.assertEqual(result.expected[0], D("1000.00"))
        self.assertEqual(result.expected[1], D("400.00"))

    def test_negative_daily_spend_is_floored(self):
        result = build_forecast(D("100"), START, 3, daily_spend=D("-5"))
        self.assertEqual(result.expected[-1], D("100.00"))

    def test_min_point(self):
        bill = Recurring("Bill", "expense", D("300"), "monthly", date(2026, 11, 3))
        pay = Recurring("Pay", "income", D("1000"), "monthly", date(2026, 11, 6))
        result = build_forecast(D("100"), START, 8, [bill, pay])
        self.assertEqual(result.min_point("expected"), (date(2026, 11, 3), D("-200.00")))


class GoalMathTests(SimpleTestCase):
    def test_reached_goal_needs_nothing(self):
        self.assertEqual(required_monthly(D("0"), START, date(2027, 1, 1)), D("0.00"))

    def test_passed_date_is_none(self):
        self.assertIsNone(required_monthly(D("100"), START, START))

    def test_monthly_amount_rounds_up(self):
        value = required_monthly(D("4000"), date(2026, 11, 8), date(2027, 7, 8))
        self.assertTrue(D("500") < value < D("510"))

    def test_minimum_one_month(self):
        self.assertEqual(required_monthly(D("300"), START, START + timedelta(days=5)), D("300.00"))


class EstimateTests(TestCase):
    def test_daily_spend_uses_covered_days_and_removes_recurring_bills(self):
        user = User.objects.create_user("est", password="pw12345678")
        account = Account.objects.create(user=user, name="Main")
        today = date(2026, 11, 8)
        Transaction.objects.create(
            user=user, account=account, kind="expense", amount=D("300"), date=date(2026, 10, 30)
        )
        self.assertEqual(estimate_daily_spend(user, today), D("30.00"))

        RecurringItem.objects.create(
            user=user, name="Rent", kind="expense", amount=D("365"), frequency="monthly", next_date=date(2026, 12, 1)
        )
        # 365 * 12 / 365 = 12.00 per day of bills removed from the 30.00 average
        self.assertEqual(estimate_daily_spend(user, today), D("18.00"))

    def test_no_history_means_zero(self):
        user = User.objects.create_user("new", password="pw12345678")
        self.assertEqual(estimate_daily_spend(user, date(2026, 11, 8)), D("0.00"))


class PlanningViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pv", password="pw12345678")
        self.account = Account.objects.create(user=self.user, name="Main", opening_balance=D("5000"))
        RecurringItem.objects.create(
            user=self.user, name="Rent", kind="expense", amount=D("2000"), frequency="monthly",
            next_date=date.today() + timedelta(days=10),
        )
        self.client.force_login(self.user)

    def test_forecast_page(self):
        response = self.client.get(reverse("forecast"), {"days": 180})
        self.assertContains(response, "Balance forecast")
        self.assertEqual(response.context["days"], 180)

    def test_forecast_survives_bad_input(self):
        self.assertEqual(self.client.get(reverse("forecast"), {"days": "abc", "daily_spend": "-3"}).status_code, 200)

    def test_what_if_purchase_lowers_balance(self):
        response = self.client.get(
            reverse("what-if"),
            {"days": 90, "purchase_amount": "6000", "purchase_date": (date.today() + timedelta(days=5)).isoformat()},
        )
        result = response.context["result"]
        self.assertEqual(result["difference"], D("-6000.00"))
        self.assertIsNotNone(result["scenario_shortfall"])

    def test_what_if_requires_a_change(self):
        response = self.client.get(reverse("what-if"), {"days": 90})
        self.assertNotIn("result", response.context)
        self.assertContains(response, "at least one change")

    def test_goals_page_and_creation(self):
        target = (date.today() + timedelta(days=240)).isoformat()
        response = self.client.post(
            reverse("goal-create"), {"name": "Laptop", "target_amount": "4000", "saved_so_far": "0", "target_date": target}
        )
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("goal-list"))
        self.assertContains(page, "Laptop")
        self.assertEqual(SavingsGoal.objects.filter(user=self.user).count(), 1)

    def test_recurring_belongs_to_user(self):
        other = User.objects.create_user("other", password="pw12345678")
        item = RecurringItem.objects.create(
            user=other, name="Theirs", kind="income", amount=D("1"), frequency="monthly", next_date=date.today()
        )
        self.assertEqual(self.client.get(reverse("recurring-update", args=[item.pk])).status_code, 404)
