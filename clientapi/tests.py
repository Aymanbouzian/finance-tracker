import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from assistant.services import AssistantUnavailable
from budgets.models import Budget
from ledger.models import Account, Category, Transaction
from planning.models import RecurringItem, SavingsGoal


@override_settings(OLLAMA_ENABLED=False)
class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.user = get_user_model().objects.create_user("api-owner", password="Api-strong-passphrase-44", first_name="Amal")
        cls.other = get_user_model().objects.create_user("api-other", password="Api-strong-passphrase-55")
        cls.account = Account.objects.create(user=cls.user, name="Everyday", opening_balance="1000.00")
        cls.category = Category.objects.create(user=cls.user, name="Food", kind="expense")
        cls.transaction = Transaction.objects.create(user=cls.user, account=cls.account, category=cls.category, kind="expense", amount="25.10", date=cls.today, description="Groceries")
        cls.budget = Budget.objects.create(user=cls.user, category=cls.category, amount=Decimal("100"), month=cls.today)
        cls.goal = SavingsGoal.objects.create(user=cls.user, name="Emergency fund", target_amount="5000", saved_so_far="500", target_date=cls.today + timedelta(days=100))
        cls.recurring = RecurringItem.objects.create(user=cls.user, name="Internet", kind="expense", amount="50", next_date=cls.today + timedelta(days=2))
        cls.foreign_account = Account.objects.create(user=cls.other, name="Private foreign account", opening_balance="999999")
        cls.foreign_category = Category.objects.create(user=cls.other, name="Private foreign category", kind="expense")
        cls.foreign_transaction = Transaction.objects.create(user=cls.other, account=cls.foreign_account, category=cls.foreign_category, kind="expense", amount="444", date=cls.today, description="Private foreign purchase")
        cls.foreign_budget = Budget.objects.create(user=cls.other, category=cls.foreign_category, amount=Decimal("900"), month=cls.today)
        cls.foreign_goal = SavingsGoal.objects.create(user=cls.other, name="Private foreign goal", target_amount="8000", target_date=cls.today + timedelta(days=90))
        cls.foreign_recurring = RecurringItem.objects.create(user=cls.other, name="Private foreign bill", kind="expense", amount="777", next_date=cls.today + timedelta(days=3))

    def setUp(self):
        cache.clear()
        self.client.force_login(self.user)

    def post(self, path, data, client=None):
        return (client or self.client).post("/api/" + path, data=json.dumps(data), content_type="application/json")

    def test_session_bootstrap_is_public_and_does_not_expose_other_user_fields(self):
        self.client.logout()
        response = self.client.get("/api/session/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertIsNone(response.json()["user"])
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", response.cookies)
        self.assertIn("no-store", response["Cache-Control"])

    def test_csrf_required_and_auth_rotates_tokens(self):
        client = Client(enforce_csrf_checks=True)
        initial = client.get("/api/session/").json()["csrfToken"]
        missing = self.post("login/", {"username": self.user.username, "password": "Api-strong-passphrase-44"}, client)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.json()["code"], "csrf_failed")
        logged_in = client.post("/api/login/", data=json.dumps({"username": self.user.username, "password": "Api-strong-passphrase-44"}), content_type="application/json", HTTP_X_CSRFTOKEN=initial)
        self.assertEqual(logged_in.status_code, 200)
        self.assertTrue(logged_in.json()["authenticated"])
        self.assertEqual(logged_in.json()["user"], {"username": self.user.username, "first_name": "Amal"})
        current = logged_in.json()["csrfToken"]
        stale = client.post("/api/accounts/", data=json.dumps({"name": "Nope", "opening_balance": "0"}), content_type="application/json", HTTP_X_CSRFTOKEN=initial)
        self.assertEqual(stale.status_code, 403)
        logout = client.post("/api/logout/", data="{}", content_type="application/json", HTTP_X_CSRFTOKEN=current)
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(logout.json()["authenticated"])
        self.assertEqual(client.get("/api/overview/").status_code, 401)

    def test_all_private_endpoints_reject_anonymous_without_redirects(self):
        self.client.logout()
        for path in ("overview/", "transactions/", "accounts/", "categories/", "budgets/", "goals/", "recurring/", "forecast/", "assistant/", "export/"):
            response = self.client.get("/api/" + path)
            self.assertEqual(response.status_code, 401, path)
            self.assertEqual(response.json()["code"], "unauthenticated")
            self.assertNotIn("Location", response)

    def test_login_failure_is_generic_and_attempts_are_limited(self):
        self.client.logout()
        known = self.post("login/", {"username": self.user.username, "password": "bad"})
        unknown = self.post("login/", {"username": "missing-user", "password": "bad"})
        self.assertEqual(known.json(), unknown.json())
        for _ in range(9):
            self.assertEqual(self.post("login/", {"username": self.user.username, "password": "bad"}).status_code, 401)
        limited = self.post("login/", {"username": self.user.username, "password": "Api-strong-passphrase-44"})
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited["Retry-After"], "600")

    def test_registration_creates_default_categories_and_session(self):
        self.client.logout()
        response = self.post("register/", {"username": "new-api-user", "first_name": "Nora", "password1": "Far-from-simple-pass-62", "password2": "Far-from-simple-pass-62"})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()["authenticated"])
        new_user = get_user_model().objects.get(username="new-api-user")
        self.assertEqual(new_user.first_name, "Nora")
        self.assertTrue(new_user.categories.filter(kind="expense").exists())
        invalid = self.post("register/", {"username": "weak-new-user", "password1": "123", "password2": "123"})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("password2", invalid.json()["errors"])

    def test_overview_is_owned_and_financial_values_are_strings(self):
        response = self.client.get("/api/overview/")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data["balance"], "974.90")
        self.assertEqual(data["expense"], "25.10")
        self.assertEqual(data["budgets"]["total_remaining"], "74.90")
        self.assertEqual(data["recent"][0]["amount"], "25.10")
        self.assertEqual(data["goals"][0]["percent"], 10)
        self.assertTrue(all(isinstance(value, str) for value in data["forecast"]["expected"]))
        self.assertNotIn("Private foreign", response.content.decode())
        self.assertIn("no-store", response["Cache-Control"])

    def test_all_resource_details_enforce_ownership_for_reads_updates_and_deletes(self):
        for resource, instance in (
            ("accounts", self.foreign_account), ("categories", self.foreign_category),
            ("transactions", self.foreign_transaction), ("budgets", self.foreign_budget),
            ("goals", self.foreign_goal), ("recurring", self.foreign_recurring),
        ):
            path = f"/api/{resource}/{instance.pk}/"
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.post(path, data="{}", content_type="application/json").status_code, 404)
            self.assertEqual(self.client.delete(path).status_code, 404)
            self.assertTrue(type(instance).objects.filter(pk=instance.pk).exists())
            self.assertNotIn("Private foreign", self.client.get(f"/api/{resource}/").content.decode())

    def test_overview_excludes_legacy_future_postings_and_new_ones_are_rejected(self):
        future = self.today + timedelta(days=2)
        legacy = Transaction.objects.create(user=self.user, account=self.account, kind="income", amount="500", date=future)
        data = self.client.get("/api/overview/").json()
        self.assertEqual(data["balance"], "974.90")
        self.assertNotIn(legacy.pk, [item["id"] for item in data["recent"]])
        rejected = self.post("transactions/", {"kind": "income", "account": self.account.pk, "amount": "50.00", "date": str(future)})
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("date", rejected.json()["errors"])

    def test_transfer_preserves_total_and_moves_exact_cents_between_accounts(self):
        destination = Account.objects.create(user=self.user, name="Savings", opening_balance="0.00")
        response = self.post("transactions/", {"kind": "transfer", "account": self.account.pk, "to_account": destination.pk, "amount": "0.10", "date": str(self.today)})
        self.assertEqual(response.status_code, 201, response.content)
        data = self.client.get("/api/overview/").json()
        balances = {item["id"]: item["balance"] for item in data["accounts"]}
        self.assertEqual(data["balance"], "974.90")
        self.assertEqual(data["income"], "0.00")
        self.assertEqual(data["expense"], "25.10")
        self.assertEqual(balances[self.account.pk], "974.80")
        self.assertEqual(balances[destination.pk], "0.10")

    def test_transaction_create_update_delete_and_user_field_cannot_override_owner(self):
        data = {"kind": "expense", "account": self.account.pk, "category": self.category.pk, "amount": "12.34", "date": str(self.today), "description": "Lunch", "user": self.other.pk}
        created = self.post("transactions/", data)
        self.assertEqual(created.status_code, 201, created.content)
        pk = created.json()["item"]["id"]
        self.assertEqual(Transaction.objects.get(pk=pk).user, self.user)
        updated = self.post(f"transactions/{pk}/", {**data, "amount": "14.50"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["item"]["amount"], "14.50")
        self.assertEqual(self.client.delete(f"/api/transactions/{pk}/").json(), {"deleted": True})
        self.assertFalse(Transaction.objects.filter(pk=pk).exists())

    def test_transactions_validate_foreign_accounts_category_type_and_transfer(self):
        base = {"kind": "expense", "account": self.account.pk, "category": self.category.pk, "amount": "10", "date": str(self.today)}
        for update, field in (({"account": self.foreign_account.pk}, "account"), ({"category": self.foreign_category.pk}, "category"), ({"amount": "-1"}, "amount"), ({"kind": "income"}, "category"), ({"kind": "transfer", "to_account": self.account.pk}, "to_account")):
            response = self.post("transactions/", {**base, **update})
            self.assertEqual(response.status_code, 400, response.content)
            self.assertIn(field, response.json()["errors"])

    def test_full_resource_crud_uses_existing_forms(self):
        payloads = {
            "accounts": {"name": "Savings", "opening_balance": "200.00"},
            "categories": {"name": "Books", "kind": "expense"},
            "budgets": {"category": self.category.pk, "month": "2027-02", "amount": "250"},
            "goals": {"name": "Laptop", "target_amount": "3000", "saved_so_far": "125", "target_date": str(self.today + timedelta(days=180))},
            "recurring": {"name": "Phone", "kind": "expense", "amount": "35", "frequency": "monthly", "next_date": str(self.today + timedelta(days=4)), "end_date": None, "active": True},
        }
        for resource, body in payloads.items():
            created = self.post(resource + "/", body)
            self.assertEqual(created.status_code, 201, (resource, created.content))
            pk = created.json()["item"]["id"]
            self.assertEqual(self.client.get(f"/api/{resource}/{pk}/").status_code, 200)
            self.assertEqual(self.post(f"{resource}/{pk}/", body).status_code, 200)
            self.assertEqual(self.client.delete(f"/api/{resource}/{pk}/").status_code, 200)

    def test_used_category_cannot_change_type_and_account_delete_matches_ledger_cascade(self):
        changed = self.post(f"categories/{self.category.pk}/", {"name": "Food", "kind": "income"})
        self.assertEqual(changed.status_code, 400)
        self.assertIn("kind", changed.json()["errors"])
        response = self.client.delete(f"/api/accounts/{self.account.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(pk=self.transaction.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.foreign_transaction.pk).exists())

    def test_transaction_filters_pagination_and_budget_month(self):
        matched = self.client.get("/api/transactions/", {"q": "grocer", "account": self.account.pk, "kind": "expense", "month": self.today.strftime("%Y-%m"), "page_size": 1}).json()
        self.assertEqual(matched["count"], 1)
        self.assertEqual(matched["results"][0]["id"], self.transaction.pk)
        self.assertEqual(self.client.get("/api/transactions/", {"q": "Private foreign"}).json()["count"], 0)
        self.assertEqual(self.client.get("/api/budgets/?month=2028-01").json()["count"], 0)
        for query in ({"page": "0"}, {"page_size": "999"}, {"month": "bad"}, {"account": "bad"}):
            self.assertEqual(self.client.get("/api/transactions/", query).status_code, 400)

    def test_forecast_and_what_if_are_decimal_server_calculations(self):
        self.user.transactions.all().delete()
        self.user.recurring_items.all().delete()
        forecast = self.client.get("/api/forecast/?days=30").json()
        self.assertEqual(forecast["start_balance"], "1000.00")
        self.assertEqual(forecast["end_expected"], "1000.00")
        self.assertEqual(len(forecast["dates"]), 31)
        scenario = self.post("what-if/", {"days": 30, "purchase_amount": "200", "purchase_date": str(self.today + timedelta(days=5))}).json()
        self.assertEqual(scenario["baseline_end"], "1000.00")
        self.assertEqual(scenario["scenario_end"], "800.00")
        self.assertEqual(scenario["difference"], "-200.00")
        self.assertEqual(self.client.get("/api/forecast/?days=45").status_code, 400)
        self.assertEqual(self.post("what-if/", {"purchase_amount": "100"}).status_code, 400)

    @patch("clientapi.views.ask_assistant", return_value="A read-only explanation")
    def test_assistant_requires_boolean_consent_and_only_sends_owned_summary(self, ask):
        for consent in (None, False, "true", 1):
            response = self.post("assistant/", {"question": "Explain", "share_summary": consent})
            self.assertEqual(response.status_code, 400)
        ask.assert_not_called()
        response = self.post("assistant/", {"question": "Explain", "share_summary": True, "base_url": "http://evil.example"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "A read-only explanation")
        summary = ask.call_args.args[1]
        self.assertNotIn("Private foreign", json.dumps(summary))
        self.assertNotIn("Groceries", json.dumps(summary))
        self.assertNotIn("base_url", summary)

    @patch("clientapi.views.ask_assistant", side_effect=AssistantUnavailable("Cannot reach Ollama."))
    def test_assistant_unavailable_is_actionable_json(self, ask):
        response = self.post("assistant/", {"question": "Explain", "share_summary": True})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "assistant_unavailable")
        snapshot = self.client.get("/api/assistant/").json()
        self.assertFalse(snapshot["enabled"])
        self.assertIn("summary", snapshot)

    def test_csv_import_is_all_or_nothing_and_export_is_owned(self):
        before = self.user.transactions.count()
        bad = SimpleUploadedFile("bad.csv", f"date,amount,description,category\n{self.today},-10,Good row,Food\nwrong,-20,Bad row,Food\n".encode(), content_type="text/csv")
        response = self.client.post("/api/import/", {"account": self.account.pk, "file": bad})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.user.transactions.count(), before)
        good = SimpleUploadedFile("good.csv", f"date,amount,description,category\n{self.today},-10,Imported lunch,Food\n".encode(), content_type="text/csv")
        response = self.client.post("/api/import/", {"account": self.account.pk, "file": good})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"imported": 1})
        exported = self.client.get("/api/export/")
        self.assertIn(b"Imported lunch", exported.content)
        self.assertNotIn(b"Private foreign", exported.content)
        self.assertIn("no-store", exported["Cache-Control"])

    def test_malformed_requests_and_unknown_routes_remain_json(self):
        for raw in ("[1,2]", "{", '{"name":{"nested":true}}'):
            response = self.client.post("/api/accounts/", data=raw, content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["code"], "invalid_json")
        self.assertEqual(self.client.post("/api/accounts/", data={"name": "x"}).status_code, 415)
        for path in ("/api/missing/", "/api/missing/deep/endpoint"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["code"], "not_found")
        self.assertEqual(self.client.put("/api/accounts/1/").status_code, 405)

    def test_import_rejects_export_format_instead_of_reversing_expense_direction(self):
        exported = self.client.get("/api/export/")
        before = self.user.transactions.count()
        upload = SimpleUploadedFile("transactions.csv", exported.content, content_type="text/csv")
        response = self.client.post("/api/import/", {"account": self.account.pk, "file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertIn("signed amounts", response.json()["error"])
        self.assertEqual(self.user.transactions.count(), before)
