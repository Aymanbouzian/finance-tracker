from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .importer import parse_amount, parse_csv
from .models import Account, Transaction

TODAY = date(2026, 11, 13)
FUTURE = TODAY + timedelta(days=1)
D = Decimal


class CSVValidationTests(SimpleTestCase):
    def setUp(self):
        clock = patch("django.utils.timezone.localdate", return_value=TODAY)
        clock.start()
        self.addCleanup(clock.stop)

    def test_oversized_header_and_field_return_errors(self):
        for text in (
            "date,amount,description," + "x" * 140000 + "\n",
            "date,amount,description\n2026-11-01,-5,Valid\n2026-11-02,-10," + "x" * 140000 + "\n",
        ):
            with self.subTest(header=text.startswith("date,amount,description,")):
                rows, errors = parse_csv(text, {})
                self.assertEqual(rows, [])
                self.assertEqual(len(errors), 1)
                self.assertIn("could not be read", errors[0])

    def test_malformed_quotes_return_an_error(self):
        rows, errors = parse_csv('date,amount,description\n2026-11-01,-5,"unfinished', {})
        self.assertEqual(rows, [])
        self.assertIn("quoting", errors[0])

    def test_rounding_cannot_exceed_decimal_field_limit(self):
        for value in ("9999999999.999", "-9999999999.999"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "after rounding"):
                parse_amount(value)
        self.assertEqual(parse_amount("9999999999.994"), D("9999999999.99"))
        self.assertEqual(parse_amount("-9999999999.994"), D("-9999999999.99"))

    def test_future_csv_dates_are_rejected_with_planning_guidance(self):
        rows, errors = parse_csv(f"date,amount,description\n{FUTURE.isoformat()},-5,Later\n", {})
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("Use recurring bills or the what-if planner", errors[0])

    def test_posted_dates_and_quoted_descriptions_still_import(self):
        rows, errors = parse_csv(f'date,amount,description\n{TODAY.isoformat()},-5,"Lunch, today"\n2026-11-01,20,Earlier\n', {})
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["description"], "Lunch, today")


class PostedLedgerValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("posted-ledger", password="ledger-password")
        cls.account = Account.objects.create(user=cls.user, name="Everyday", opening_balance=D("500"))
        cls.savings = Account.objects.create(user=cls.user, name="Savings")

    def setUp(self):
        clock = patch("django.utils.timezone.localdate", return_value=TODAY)
        clock.start()
        self.addCleanup(clock.stop)
        self.client.force_login(self.user)

    def test_model_rejects_future_dates_for_every_transaction_kind(self):
        for kind in (Transaction.INCOME, Transaction.EXPENSE, Transaction.TRANSFER):
            transaction = Transaction(
                user=self.user, account=self.account, kind=kind, amount=D("5"), date=FUTURE,
                to_account=self.savings if kind == Transaction.TRANSFER else None,
            )
            with self.subTest(kind=kind), self.assertRaises(ValidationError) as error:
                transaction.full_clean()
            self.assertIn("date", error.exception.message_dict)
            self.assertIn("what-if planner", error.exception.message_dict["date"][0])

    def test_invalid_date_still_produces_validation_error(self):
        transaction = Transaction(user=self.user, account=self.account, kind="expense", amount=D("5"), date="not-a-date")
        with self.assertRaises(ValidationError) as error:
            transaction.full_clean()
        self.assertIn("date", error.exception.message_dict)

    def test_create_form_rejects_future_transaction_and_accepts_today(self):
        data = {"account": self.account.pk, "kind": "expense", "amount": "5", "date": FUTURE.isoformat(), "description": "Later"}
        response = self.client.post(reverse("transaction-create"), data)
        self.assertContains(response, "Use recurring bills or the what-if planner")
        self.assertEqual(Transaction.objects.count(), 0)
        data["date"] = TODAY.isoformat()
        response = self.client.post(reverse("transaction-create"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.get().date, TODAY)

    def test_import_errors_do_not_save_other_valid_rows(self):
        for bad_row in (
            f"{FUTURE.isoformat()},-10,Future",
            f"{TODAY.isoformat()},9999999999.999,Too big",
            f"{TODAY.isoformat()},-10," + "x" * 140000,
        ):
            with self.subTest(prefix=bad_row[:50]):
                text = f"date,amount,description\n{TODAY.isoformat()},-5,Valid\n{bad_row}\n"
                upload = SimpleUploadedFile("statement.csv", text.encode())
                response = self.client.post(reverse("import-csv"), {"account": self.account.pk, "file": upload})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["errors"])
                self.assertEqual(Transaction.objects.count(), 0)

    def test_preexisting_future_rows_remain_stored_without_affecting_current_balance(self):
        # Existing data remains intact; this simulates a row stored before the rule.
        existing = Transaction.objects.create(user=self.user, account=self.account, kind="expense", amount=D("40"), date=FUTURE)
        self.assertEqual(self.account.balance, D("500"))
        self.assertContains(self.client.get(reverse("transaction-list")), "40.00")
        self.assertTrue(Transaction.objects.filter(pk=existing.pk).exists())
