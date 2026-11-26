import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import AssistantForm
from .services import AssistantUnavailable, ask_assistant, configuration, connection_status, financial_summary


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def assistant_view(request):
    summary = financial_summary(request.user)
    form = AssistantForm(request.POST if request.method == "POST" else None)
    answer = None
    error = None
    status = None
    if request.method == "POST" and form.is_valid():
        try:
            answer = ask_assistant(form.cleaned_data["question"], summary)
            form = AssistantForm(initial={"question": form.cleaned_data["question"]})
            status = {"ready": True, "label": "Connected", "detail": "Your configured model answered this question."}
        except AssistantUnavailable as exception:
            error = str(exception)
            status = {"ready": False, "label": "Unavailable", "detail": error}
    if status is None:
        status = connection_status()
    return render(request, "assistant/home.html", {
        "form": form,
        "summary": summary,
        "snapshot_json": json.dumps(summary, indent=2, ensure_ascii=False),
        "answer": answer,
        "assistant_error": error,
        "ai_status": status,
        "ai_config": configuration(),
    })

