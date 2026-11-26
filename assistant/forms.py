from django import forms

from ledger.forms import style_fields


class AssistantForm(forms.Form):
    question = forms.CharField(
        label="What would you like to understand?",
        max_length=1200,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "How is my spending this month, and what should I keep an eye on?",
        }),
    )
    share_summary = forms.BooleanField(
        required=True,
        label="Send my question and the summary below to my configured Ollama server for this answer.",
        error_messages={"required": "Confirm sharing this summary before asking the assistant."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
