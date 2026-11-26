import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from ledger.models import Account, Category, Transaction

from .services import (
    MAX_RESPONSE_BYTES,
    AssistantUnavailable,
    NoRedirects,
    _request,
    ask_assistant,
    connection_status,
    financial_summary,
)


@override_settings(OLLAMA_ENABLED=True, OLLAMA_BASE_URL="http://127.0.0.1:11434", OLLAMA_MODEL="qwen3:4b", OLLAMA_TIMEOUT=45)
class OllamaClientTests(SimpleTestCase):
    def response(self, data):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(data).encode()
        return opener

    @patch("assistant.services.build_opener")
    def test_chat_is_bounded_non_streaming_and_only_uses_configured_url(self, build):
        build.return_value = self.response({"message": {"content": "A useful answer"}})
        result = ask_assistant("Explain my expenses", {"balance": "42.50"})
        request = build.return_value.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(payload["model"], "qwen3:4b")
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["think"])
        self.assertEqual(payload["options"]["num_predict"], 750)
        self.assertNotIn("tools", payload)
        self.assertEqual(build.return_value.open.call_args.kwargs["timeout"], 45)
        self.assertEqual(result, "A useful answer")

    @override_settings(OLLAMA_ENABLED=False)
    @patch("assistant.services.build_opener")
    def test_disabled_never_opens_network(self, build):
        self.assertEqual(connection_status()["label"], "Not enabled")
        with self.assertRaisesMessage(AssistantUnavailable, "switched off"):
            ask_assistant("hello", {})
        build.assert_not_called()

    @patch("assistant.services.build_opener")
    def test_status_checks_selected_model(self, build):
        build.return_value = self.response({"models": [{"name": "qwen3:4b"}]})
        self.assertTrue(connection_status()["ready"])
        self.assertEqual(build.return_value.open.call_args.kwargs["timeout"], 2)
        build.return_value = self.response({"models": [{"name": "another:latest"}]})
        self.assertEqual(connection_status()["label"], "Model needed")

    @patch("assistant.services.build_opener")
    def test_bad_model_list_returns_unavailable(self, build):
        build.return_value = self.response({"models": "invalid"})
        self.assertEqual(connection_status()["label"], "Unavailable")
        build.return_value = self.response({"models": [{"name": []}]})
        self.assertEqual(connection_status()["label"], "Model needed")

    @patch("assistant.services.build_opener")
    def test_network_failure_is_actionable_without_raw_details(self, build):
        build.return_value.open.side_effect = URLError("private-secret-in-error")
        with self.assertRaisesMessage(AssistantUnavailable, "Cannot reach Ollama") as caught:
            ask_assistant("hello", {})
        self.assertNotIn("private-secret", str(caught.exception))
        self.assertFalse(connection_status()["ready"])

    @patch("assistant.services.build_opener")
    def test_timeout(self, build):
        build.return_value.open.side_effect = TimeoutError()
        with self.assertRaisesMessage(AssistantUnavailable, "took too long"):
            ask_assistant("hello", {})

    @patch("assistant.services.build_opener")
    def test_missing_model(self, build):
        build.return_value.open.side_effect = HTTPError("url", 404, "missing", {}, BytesIO())
        with self.assertRaisesMessage(AssistantUnavailable, "Pull the model"):
            ask_assistant("hello", {})

    @patch("assistant.services.build_opener")
    def test_unreadable_empty_and_oversized_responses(self, build):
        for payload in ({}, {"message": {}}, {"message": {"content": " "}}, {"message": []}):
            with self.subTest(payload=payload):
                build.return_value = self.response(payload)
                with self.assertRaisesMessage(AssistantUnavailable, "no answer"):
                    ask_assistant("hello", {})
        build.return_value.open.return_value.__enter__.return_value.read.return_value = b"not-json"
        with self.assertRaisesMessage(AssistantUnavailable, "unreadable"):
            _request("/api/tags")
        build.return_value.open.return_value.__enter__.return_value.read.return_value = b"x" * (MAX_RESPONSE_BYTES + 1)
        with self.assertRaisesMessage(AssistantUnavailable, "oversized"):
            _request("/api/tags")

    @patch("assistant.services.build_opener")
    def test_invalid_server_config_never_opens_network(self, build):
        for url in ("file:///tmp/model", "http://user:password@localhost", "http://localhost:bad", "http://localhost?token=secret"):
            with self.subTest(url=url), override_settings(OLLAMA_BASE_URL=url):
                with self.assertRaisesMessage(AssistantUnavailable, "address is invalid"):
                    _request("/api/tags")
        build.assert_not_called()

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 307, "", {}, "https://another.example"))


@override_settings(OLLAMA_ENABLED=False)
class AssistantViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("owner", password="some-long-password")
        cls.other = get_user_model().objects.create_user("someone-else", password="some-long-password")
        cls.account = Account.objects.create(user=cls.user, name="private-account-name", opening_balance=Decimal("1000"))
        other_account = Account.objects.create(user=cls.other, name="another-private-account", opening_balance=Decimal("999999"))
        cls.food = Category.objects.create(user=cls.user, name="Food", kind="expense")
        other_category = Category.objects.create(user=cls.other, name="secret-other-category", kind="expense")
        Transaction.objects.create(user=cls.user, account=cls.account, kind="expense", amount=Decimal("25"), category=cls.food, date=date(2026, 11, 2), description="private-transaction-text")
        Transaction.objects.create(user=cls.other, account=other_account, kind="expense", amount=Decimal("777"), category=other_category, date=date(2026, 11, 2), description="other-private-text")

    def setUp(self):
        self.client.force_login(self.user)

    def test_summary_is_owned_aggregates_only(self):
        summary = financial_summary(self.user, date(2026, 11, 13))
        text = json.dumps(summary)
        self.assertEqual(summary["balance"], "975.00")
        self.assertEqual(summary["month_to_date_expenses"], "25")
        self.assertEqual(
            [(row["category"], Decimal(row["amount"])) for row in summary["top_expense_categories"]],
            [("Food", Decimal("25.00"))],
        )
        for secret in ("private-account-name", "private-transaction-text", "secret-other-category", "other-private-text", "999999", "777"):
            self.assertNotIn(secret, text)

    def test_anonymous_cannot_read_or_ask(self):
        self.client.logout()
        for method in (self.client.get, self.client.post):
            response = method(reverse("assistant"))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response["Location"])

    @patch("assistant.services.build_opener")
    def test_offline_summary_still_renders_and_is_not_cached(self, build):
        response = self.client.get(reverse("assistant"))
        self.assertContains(response, "Your money companion")
        self.assertContains(response, "Not enabled")
        self.assertIn("no-store", response["Cache-Control"])
        build.assert_not_called()

    @patch("assistant.views.ask_assistant")
    def test_consent_is_required_before_question_is_sent(self, ask):
        response = self.client.post(reverse("assistant"), {"question": "Explain my spending"})
        self.assertContains(response, "Confirm sharing this summary")
        ask.assert_not_called()

    @patch("assistant.views.ask_assistant")
    def test_empty_and_overlong_question_are_not_sent(self, ask):
        for question in ("", "x" * 1201):
            response = self.client.post(reverse("assistant"), {"question": question, "share_summary": "on"})
            self.assertEqual(response.status_code, 200)
        ask.assert_not_called()

    @patch("assistant.views.ask_assistant", return_value='<script>alert("hello")</script>')
    def test_model_output_is_escaped_and_consent_resets(self, ask):
        response = self.client.post(reverse("assistant"), {"question": "Explain", "share_summary": "on", "base_url": "https://evil.example"})
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("hello")</script>')
        self.assertEqual(ask.call_args.args[0], "Explain")
        self.assertNotIn("base_url", ask.call_args.args[1])
        self.assertFalse(response.context["form"]["share_summary"].value())
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 1)

    @patch("assistant.views.ask_assistant", side_effect=AssistantUnavailable("Cannot reach Ollama."))
    def test_unavailable_answer_keeps_snapshot_and_question(self, ask):
        response = self.client.post(reverse("assistant"), {"question": "Explain", "share_summary": "on"})
        self.assertContains(response, "Cannot reach Ollama.")
        self.assertContains(response, "A snapshot of your month")
        self.assertEqual(response.context["form"]["question"].value(), "Explain")
