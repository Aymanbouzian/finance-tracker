"""Serve the public Flutter release shell beside the session-authenticated API."""

import mimetypes
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.utils.http import http_date
from django.views.decorators.http import require_safe


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".svg": "image/svg+xml",
    ".bin": "application/octet-stream",
}


@require_safe
def home(request):
    return redirect("flutter-app")


def _inside(root, relative):
    """Resolve symlinks too; a build asset must stay inside the configured root."""
    try:
        candidate = (root / relative).resolve()
    except (OSError, RuntimeError, ValueError):
        raise Http404 from None
    if not candidate.is_relative_to(root):
        raise Http404
    return candidate


@require_safe
def app(request, asset_path=""):
    # URLs use POSIX separators even when the server runs on Windows. Reject
    # drive/ADS syntax, hidden files and traversal before filesystem resolution.
    parts = PurePosixPath(asset_path).parts
    if ("\\" in asset_path or ":" in asset_path or "\x00" in asset_path
            or asset_path.startswith("/") or any(part.startswith(".") for part in parts)):
        raise Http404
    root = Path(settings.FLUTTER_WEB_DIR).resolve()
    shell = _inside(root, "index.html")
    if not shell.is_file():
        response = HttpResponse(
            "PocketLedger's Flutter build is not available yet. "
            "From flutter_app, run: flutter build web --release --base-href /app/ "
            "--no-web-resources-cdn. Then reload this page. "
            "The previous interface remains available at /classic/.",
            content_type="text/plain; charset=utf-8", status=503,
        )
        response["Cache-Control"] = "no-store"
        response["Retry-After"] = "60"
        return response
    candidate = _inside(root, asset_path or "index.html")
    if not candidate.is_file():
        # SPA deep links can load the shell. Missing scripts/images/fonts must
        # produce 404 rather than HTML with a misleading successful response.
        if PurePosixPath(asset_path).suffix:
            raise Http404
        candidate = shell
    try:
        handle = candidate.open("rb")
    except (OSError, ValueError):
        raise Http404 from None
    content_type = CONTENT_TYPES.get(candidate.suffix.lower()) or mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    # Flutter runtime filenames are stable across releases, so always
    # revalidate cached assets. The shell has no user-specific content.
    response.pocketledger_public = True
    response["Cache-Control"] = "public, no-cache, must-revalidate"
    response["Last-Modified"] = http_date(candidate.stat().st_mtime)
    response["X-Content-Type-Options"] = "nosniff"
    return response
