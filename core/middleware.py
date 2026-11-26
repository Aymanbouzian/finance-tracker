from django.utils.cache import patch_cache_control


class PrivateResponseMiddleware:
    """Keep dynamic pages, exports and API responses out of shared/browser caches."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "").split(";", 1)[0]
        if not getattr(response, "pocketledger_public", False) and content_type in {
            "text/html", "text/csv", "application/json",
        }:
            patch_cache_control(response, private=True, no_store=True, no_cache=True, max_age=0, must_revalidate=True)
        return response
