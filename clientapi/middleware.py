from django.http import JsonResponse
from django.utils.cache import patch_cache_control


class ApiResponseMiddleware:
    """Keep API errors JSON and prevent financial responses being cached."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            if response.status_code >= 400 and response.get("Content-Type", "").split(";", 1)[0] != "application/json":
                status = response.status_code
                code, message = {
                    400: ("bad_request", "The request could not be processed."),
                    403: ("forbidden", "This request was not allowed. Refresh your session and try again."),
                    404: ("not_found", "The requested record was not found."),
                    405: ("method_not_allowed", "This request method is not supported."),
                    413: ("request_too_large", "The request is too large."),
                }.get(status, ("server_error", "The server could not complete this request."))
                response = JsonResponse({"error": message, "code": code}, status=status)
            patch_cache_control(response, private=True, no_store=True, no_cache=True, max_age=0)
        return response
