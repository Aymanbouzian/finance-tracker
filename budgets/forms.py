from datetime import datetime

from django import forms

from ledger.forms import UserModelForm
from ledger.models import Category, Transaction

from .models import Budget


class MonthInput(forms.DateInput):
    input_type = "month"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m", **kwargs)


class BudgetForm(UserModelForm):
    month = forms.DateField(input_formats=["%Y-%m"], widget=MonthInput())

    class Meta:
        model = Budget
        fields = ["category", "month", "amount"]
        labels = {"amount": "Monthly limit"}
        help_texts = {"amount": "Set a realistic limit. Your recorded expenses update this budget automatically."}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user, kind=Transaction.EXPENSE)
        self.fields["amount"].widget.attrs.update({"min": "0.01", "step": "0.01", "inputmode": "decimal"})

    def clean(self):
        cleaned = super().clean()
        category, month = cleaned.get("category"), cleaned.get("month")
        if category and month:
            duplicate = Budget.objects.filter(user=self.user, category=category, month=month)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("category", "This category already has a budget for that month. Edit the existing budget instead.")
        return cleaned


def parse_month(value, fallback):
    """Accept the browser's YYYY-MM format; invalid URL filters use the current month."""
    try:
        parsed = datetime.strptime(value, "%Y-%m").date()
        # strptime accepts non-padded months; canonical URLs remain YYYY-MM.
        return parsed.replace(day=1)
    except (TypeError, ValueError):
        return fallback.replace(day=1)
