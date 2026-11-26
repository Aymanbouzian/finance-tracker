from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Account, Transaction
from .services import monthly_history


class MonthlyHistoryCutoffTests(TestCase):
    def test_current_month_stops_at_today_but_previous_month_is_complete(self):
        user = get_user_model().objects.create_user("history-reader")
        account = Account.objects.create(user=user, name="Everyday")
        for on, kind, amount in (
            (date(2026, 10, 31), "income", "200"),
            (date(2026, 10, 31), "expense", "50"),
            (date(2026, 11, 1), "income", "100"),
            (date(2026, 11, 13), "expense", "10"),
            # Direct database rows cover existing future-dated imports too.
            (date(2026, 11, 14), "income", "9999"),
            (date(2026, 11, 30), "expense", "8888"),
        ):
            Transaction.objects.create(user=user, account=account, date=on, kind=kind, amount=Decimal(amount))

        result = monthly_history(user, date(2026, 11, 13), months=2)
        self.assertEqual(result, [
            {"label": "Oct 2026", "income": Decimal("200"), "expense": Decimal("50")},
            {"label": "Nov 2026", "income": Decimal("100"), "expense": Decimal("10")},
        ])
