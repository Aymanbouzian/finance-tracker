from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from . import flutter


class FlutterServingTests(SimpleTestCase):
    def setUp(self):
        self.workspace = TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name) / "web"
        self.root.mkdir()
        (self.root / "index.html").write_text('<base href="/app/"><title>PocketLedger</title>', encoding="utf-8")
        self.override = self.settings(FLUTTER_WEB_DIR=self.root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.factory = RequestFactory()

    def body(self, response):
        try:
            return b"".join(response.streaming_content)
        finally:
            response.close()

    def test_root_redirects_to_flutter_and_classic_keeps_its_route_name(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/app/", fetch_redirect_response=False)
        self.assertEqual(reverse("dashboard"), "/classic/")
        self.assertEqual(reverse("flutter-app"), "/app/")

    def test_shell_is_public_and_revalidated_without_a_login(self):
        response = self.client.get("/app/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PocketLedger", self.body(response))
        self.assertTrue(response.pocketledger_public)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(response["Cache-Control"], "public, no-cache, must-revalidate")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("Last-Modified", response)
        self.assertFalse(response.cookies)

    def test_assets_use_runtime_mime_types_and_file_streaming(self):
        for name, content_type in (
            ("canvaskit.wasm", "application/wasm"),
            ("main.dart.js", "application/javascript; charset=utf-8"),
            ("module.mjs", "application/javascript; charset=utf-8"),
            ("manifest.json", "application/json"),
            ("manifest.webmanifest", "application/manifest+json"),
            ("font.woff2", "font/woff2"),
            ("font.ttf", "font/ttf"),
        ):
            (self.root / name).write_bytes(b"public build content")
            response = self.client.get("/app/" + name)
            self.assertEqual(response.status_code, 200, name)
            self.assertTrue(response.streaming)
            self.assertEqual(response["Content-Type"], content_type)
            self.assertEqual(self.body(response), b"public build content")

    def test_extensionless_deep_link_gets_shell_but_missing_asset_is_404(self):
        response = self.client.get("/app/planning/goals")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PocketLedger", self.body(response))
        for path in ("missing.js", "assets/absent.png", "assets/FontManifest.json"):
            self.assertEqual(self.client.get("/app/" + path).status_code, 404, path)

    def test_traversal_hidden_paths_and_windows_drive_syntax_are_rejected(self):
        (self.root.parent / "secret.txt").write_text("private", encoding="utf-8")
        for path in ("../secret.txt", "assets/../../secret.txt", "assets/../index.html", ".env", "assets/.secret", "C:/secret.txt", "C:\\secret.txt", "..\\secret.txt", "index.html:secret", "/secret.txt", "bad\x00.js"):
            with self.subTest(path=path), self.assertRaises(Http404):
                flutter.app(self.factory.get("/app/"), asset_path=path)

    def test_resolved_asset_and_shell_cannot_escape_through_symlink(self):
        # Mock canonical resolution so this runs even on Windows hosts without
        # the optional privilege required to create filesystem symlinks.
        original = Path.resolve
        outside = self.root.parent / "secret.txt"
        outside.write_text("private", encoding="utf-8")

        def resolved(path, *args, **kwargs):
            if path.name == "linked.js":
                return outside
            return original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolved), self.assertRaises(Http404):
            flutter.app(self.factory.get("/app/linked.js"), asset_path="linked.js")

        def shell_resolved(path, *args, **kwargs):
            if path.name == "index.html":
                return outside
            return original(path, *args, **kwargs)

        with patch.object(Path, "resolve", shell_resolved), self.assertRaises(Http404):
            flutter.app(self.factory.get("/app/"))

    def test_missing_build_returns_actionable_503(self):
        with self.settings(FLUTTER_WEB_DIR=self.root / "not-built"):
            response = self.client.get("/app/")
        self.assertEqual(response.status_code, 503)
        self.assertIn(b"flutter build web", response.content)
        self.assertIn(b"/classic/", response.content)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_only_safe_methods_are_supported_and_head_has_no_body(self):
        self.assertEqual(self.client.post("/app/", data={}).status_code, 405)
        self.assertEqual(self.client.post("/", data={}).status_code, 405)
        response = self.client.head("/app/index.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.body(response), b"")
