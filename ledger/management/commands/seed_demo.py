import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from ledger.dates import add_months
from ledger.models import Account, Category, Transaction
from ledger.services import create_default_categories
from planning.models import RecurringItem, SavingsGoal

DEMO_USER = "demo"
DEMO_PASSWORD = "demo12345"


class Command(BaseCommand):
    help = f"Create a demo user ('{DEMO_USER}' / '{DEMO_PASSWORD}') with ~90 days of sample data."

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username=DEMO_USER).exists():
            self.stdout.write("Demo user already exists; nothing to do.")
            return

        rng = random.Random(42)
        today = timezone.localdate()
        user = User.objects.create_user(DEMO_USER, password=DEMO_PASSWORD)
        create_default_categories(user)
        cat = {c.name: c for c in Category.objects.filter(user=user)}
        checking = Account.objects.create(user=user, name="Checking", opening_balance=Decimal("3000"))
        Account.objects.create(user=user, name="Savings", opening_balance=Decimal("5000"))

        def add(day, kind, amount, category, text):
            Transaction.objects.create(
                user=user, account=checking, kind=kind, amount=Decimal(amount), date=day,
                category=cat[category], description=text,
            )

        this_month = today.replace(day=1)
        for back in range(4):
            first = add_months(this_month, -back)
            for day_of_month, kind, amount, category, text in [
                (1, Transaction.INCOME, "6000", "Salary", "Salary"),
                (5, Transaction.EXPENSE, "2000", "Housing", "Rent"),
                (10, Transaction.EXPENSE, "300", "Utilities", "Internet"),
            ]:
                day = first.replace(day=day_of_month)
                if day <= today and (today - day).days < 90:
                    add(day, kind, amount, category, text)

        for back in range(90):
            day = today - timedelta(days=back)
            if back % 3 == 0:
                add(day, Transaction.EXPENSE, rng.randint(40, 250), "Food", "Groceries")
            if back % 2 == 0:
                add(day, Transaction.EXPENSE, rng.randint(10, 60), "Transport", "Transport")
            if back % 11 == 0:
                add(day, Transaction.EXPENSE, rng.randint(50, 200), "Entertainment", "Leisure")

        def next_on(day_of_month):
            candidate = date(today.year, today.month, day_of_month)
            return candidate if candidate > today else add_months(candidate, 1)

        for name, kind, amount, day_of_month in [
            ("Salary", Transaction.INCOME, "6000", 1),
            ("Rent", Transaction.EXPENSE, "2000", 5),
            ("Internet", Transaction.EXPENSE, "300", 10),
        ]:
            RecurringItem.objects.create(
                user=user, name=name, kind=kind, amount=Decimal(amount), next_date=next_on(day_of_month)
            )
        SavingsGoal.objects.create(
            user=user, name="New laptop", target_amount=Decimal("8000"),
            saved_so_far=Decimal("1000"), target_date=add_months(today, 6),
        )
        self.stdout.write(self.style.SUCCESS(f"Created demo user '{DEMO_USER}' with password '{DEMO_PASSWORD}'."))
