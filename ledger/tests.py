from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .importer import parse_csv
from .models import Account, Category, Transaction
from .services import total_balance, totals_between

User = get_user_model()
D = Decimal


class LedgerMathTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ann", password="pw12345678")
        self.checking = Account.objects.create(user=self.user, name="Checking", opening_balance=D("1000"))
        self.savings = Account.objects.create(user=self.user, name="Savings", opening_balance=D("0"))

    def add(self, **kwargs):
        t = Transaction(user=self.user, date=kwargs.pop("date", date(2026, 11, 1)), **kwargs)
        t.full_clean()
        t.save()
        return t

    def test_balances_with_transfer(self):
        self.add(account=self.checking, kind="income", amount=D("500"))
        self.add(account=self.checking, kind="expense", amount=D("200"))
        self.add(account=self.checking, kind="transfer", amount=D("300"), to_account=self.savings)
        self.assertEqual(self.checking.balance, D("1000"))
        self.assertEqual(self.savings.balance, D("300"))
        self.assertEqual(total_balance(self.user), D("1300"))

    def test_transfers_are_not_income_or_spending(self):
        self.add(account=self.checking, kind="income", amount=D("500"))
        self.add(account=self.checking, kind="expense", amount=D("200"))
        self.add(account=self.checking, kind="transfer", amount=D("300"), to_account=self.savings)
        income, expense = totals_between(self.user, date(2026, 11, 1), date(2026, 11, 30))
        self.assertEqual((income, expense), (D("500"), D("200")))

    def test_transfer_needs_a_different_destination(self):
        with self.assertRaises(ValidationError):
            self.add(account=self.checking, kind="transfer", amount=D("10"))
        with self.assertRaises(ValidationError):
            self.add(account=self.checking, kind="transfer", amount=D("10"), to_account=self.checking)

    def test_category_must_match_kind(self):
        food = Category.objects.create(user=self.user, name="Food", kind="expense")
        with self.assertRaises(ValidationError):
            self.add(account=self.checking, kind="income", amount=D("10"), category=food)

    def test_cannot_use_another_users_account(self):
        other = User.objects.create_user("bob", password="pw12345678")
        theirs = Account.objects.create(user=other, name="Theirs")
        with self.assertRaises(ValidationError):
            self.add(account=theirs, kind="expense", amount=D("10"))

    def test_amount_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.add(account=self.checking, kind="expense", amount=D("0"))


class IsolationTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", password="pw12345678")
        self.b = User.objects.create_user("b", password="pw12345678")
        account = Account.objects.create(user=self.a, name="Main")
        self.tx = Transaction.objects.create(
            user=self.a, account=account, kind="expense", amount=D("5"),
            date=date(2026, 11, 1), description="secret-lunch",
        )

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_other_user_cannot_see_or_edit(self):
        self.client.force_login(self.b)
        self.assertNotContains(self.client.get(reverse("transaction-list")), "secret-lunch")
        self.assertEqual(self.client.get(reverse("transaction-update", args=[self.tx.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("transaction-delete", args=[self.tx.pk])).status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=self.tx.pk).exists())

    def test_owner_sees_their_data(self):
        self.client.force_login(self.a)
        self.assertContains(self.client.get(reverse("transaction-list")), "secret-lunch")


class ImporterTests(TestCase):
    def test_parses_signed_amounts_and_formats(self):
        categories = {
            "food": Category(name="Food", kind="expense"),
            "salary": Category(name="Salary", kind="income"),
        }
        text = (
            "date,amount,description,category\n"
            "2026-11-01,-45.50,Lunch,Food\n"
            '01/11/2026,"1 200,00",Pay,Salary\n'
            "02/11/2026,-10,Mismatch,Salary\n"
        )
        rows, errors = parse_csv(text, categories)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["kind"], "expense")
        self.assertEqual(rows[0]["amount"], D("45.50"))
        self.assertEqual(rows[1]["kind"], "income")
        self.assertEqual(rows[1]["amount"], D("1200.00"))
        self.assertIsNotNone(rows[1]["category"])
        self.assertIsNone(rows[2]["category"])  # income category on an expense row is dropped

    def test_reports_bad_rows(self):
        text = "date,amount,description\n2026-13-45,5,Bad date\n2026-11-01,0,Zero\n2026-11-01,abc,Text\n"
        rows, errors = parse_csv(text, {})
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 3)

    def test_missing_columns(self):
        rows, errors = parse_csv("date,description\n2026-11-01,x\n", {})
        self.assertEqual(rows, [])
        self.assertIn("amount", errors[0])

    def test_import_view_is_all_or_nothing(self):
        user = User.objects.create_user("imp", password="pw12345678")
        account = Account.objects.create(user=user, name="Main")
        self.client.force_login(user)

        good = SimpleUploadedFile("s.csv", b"date,amount,description\n2026-11-01,-5,A\n2026-11-02,100,B\n")
        self.client.post(reverse("import-csv"), {"account": account.pk, "file": good})
        self.assertEqual(Transaction.objects.filter(user=user).count(), 2)

        bad = SimpleUploadedFile("s.csv", b"date,amount,description\n2026-11-03,-5,C\nnot-a-date,1,D\n")
        response = self.client.post(reverse("import-csv"), {"account": account.pk, "file": bad})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.filter(user=user).count(), 2)

    def test_export_neutralises_formulas(self):
        user = User.objects.create_user("exp", password="pw12345678")
        account = Account.objects.create(user=user, name="Main")
        Transaction.objects.create(
            user=user, account=account, kind="expense", amount=D("5"),
            date=date(2026, 11, 1), description="=HYPERLINK(1)",
        )
        self.client.force_login(user)
        body = self.client.get(reverse("export-csv")).content.decode()
        self.assertIn("'=HYPERLINK(1)", body)


class RegistrationTests(TestCase):
    def test_register_creates_default_categories(self):
        response = self.client.post(
            reverse("register"),
            {"username": "newbie", "password1": "a-Strong-pass-123", "password2": "a-Strong-pass-123"},
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newbie")
        self.assertTrue(Category.objects.filter(user=user, name="Salary").exists())
