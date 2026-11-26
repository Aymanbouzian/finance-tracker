import json
import re
import struct

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase

from . import views
from .middleware import PrivateResponseMiddleware


class PWAResourceTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_manifest_has_install_metadata_and_real_png_icons(self):
        response = views.manifest(self.factory.get("/manifest.webmanifest"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        data = json.loads(response.content)
        self.assertEqual(data["start_url"], "/")
        self.assertEqual(data["scope"], "/")
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["name"], "PocketLedger")
        self.assertFalse(data["prefer_related_applications"])
        for icon, size in zip(data["icons"], (192, 512)):
            self.assertEqual(icon["sizes"], f"{size}x{size}")
            image = (settings.BASE_DIR / "static" / "pwa" / f"icon-{size}.png").read_bytes()
            self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", image[16:24]), (size, size))

    def test_service_worker_is_root_scoped_and_public_assets_are_explicit(self):
        response = views.service_worker(self.factory.get("/service-worker.js"))
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertIn("no-cache", response["Cache-Control"])
        source = response.content.decode()
        self.assertNotIn("__PUBLIC_ASSETS__", source)
        self.assertNotIn("__CACHE_VERSION__", source)
        match = re.search(r"const PUBLIC_ASSETS = (\[.*?\]);", source)
        assets = json.loads(match.group(1))
        self.assertIn("/offline/", assets)
        self.assertTrue(all(url == "/offline/" or url.startswith("/static/") for url in assets))
        self.assertNotIn("/", assets)
        self.assertNotIn("/accounts/login/", assets)

    def test_offline_page_is_public_and_does_not_promise_offline_writes(self):
        response = views.offline(self.factory.get("/offline/"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.pocketledger_public)
        self.assertIn(b"changes are not queued", response.content)
        self.assertFalse(response.cookies)

    def test_pwa_resources_reject_post(self):
        request = self.factory.post("/manifest.webmanifest")
        for view in (views.manifest, views.service_worker, views.offline, views.install):
            self.assertEqual(view(request).status_code, 405)


class PrivateResponseTests(SimpleTestCase):
    def test_dynamic_html_json_and_csv_are_never_cached(self):
        request = RequestFactory().get("/")
        for response in (
            HttpResponse("account balance"),
            JsonResponse({"balance": "100"}),
            HttpResponse("date,amount", content_type="text/csv"),
        ):
            protected = PrivateResponseMiddleware(lambda _: response)(request)
            self.assertIn("no-store", protected["Cache-Control"])
            self.assertIn("private", protected["Cache-Control"])

    def test_public_offline_page_keeps_explicit_cache_policy(self):
        request = RequestFactory().get("/offline/")
        response = PrivateResponseMiddleware(views.offline)(request)
        self.assertEqual(response["Cache-Control"], "public, max-age=300")
