"""Public installation resources. No user records are embedded in these responses."""

import hashlib
import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.http import require_safe


def _public(response):
    response.pocketledger_public = True
    return response


@require_safe
def manifest(request):
    data = {
        "id": "/",
        "name": "PocketLedger",
        "short_name": "PocketLedger",
        "description": "Your money, with a little more clarity. Track, budget and plan.",
        "lang": "en",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f7f8fa",
        "theme_color": "#153f36",
        "categories": ["finance", "productivity"],
        "prefer_related_applications": False,
        "icons": [
            {"src": static("pwa/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": static("pwa/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "shortcuts": [
            {"name": "Add transaction", "url": "/transactions/new/"},
            {"name": "Budgets", "url": "/budgets/"},
        ],
    }
    response = JsonResponse(data, content_type="application/manifest+json")
    response["Cache-Control"] = "public, max-age=300"
    return _public(response)


@require_safe
def service_worker(request):
    offline_url = reverse("pwa-offline")
    public_files = [
        "pwa/icon-192.png", "pwa/icon-512.png", "pwa/install.js",
        "app.css", "app.js", "vendor/bootstrap.min.css", "vendor/chart.umd.min.js",
    ]
    # Including content hashes in the worker updates its public cache when a
    # deployment changes assets, even when their filenames stay the same.
    version = hashlib.sha256()
    available = []
    for filename in ["pwa/offline.html", *public_files]:
        path = settings.BASE_DIR / "static" / filename
        if path.is_file():
            version.update(filename.encode())
            version.update(path.read_bytes())
            if filename in public_files:
                available.append(filename)
    assets = [offline_url, *[static(filename) for filename in available]]
    source = (settings.BASE_DIR / "static" / "pwa" / "service-worker.js").read_text(encoding="utf-8")
    source = source.replace("__PUBLIC_ASSETS__", json.dumps(assets)).replace("__OFFLINE_URL__", json.dumps(offline_url))
    source = source.replace("__CACHE_VERSION__", version.hexdigest()[:16])
    response = HttpResponse(source, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    return _public(response)


@require_safe
def offline(request):
    source = (settings.BASE_DIR / "static" / "pwa" / "offline.html").read_text(encoding="utf-8")
    response = HttpResponse(source, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    return _public(response)


@require_safe
def install(request):
    return render(request, "core/install.html")
