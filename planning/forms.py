from django import forms

from ledger.forms import DateInput, UserModelForm, style_fields

from .models import RecurringItem, SavingsGoal

DAY_CHOICES = [(30, "30 days"), (60, "60 days"), (90, "90 days"), (180, "6 months"), (365, "1 year")]


class RecurringItemForm(UserModelForm):
    class Meta:
        model = RecurringItem
        fields = ["name", "kind", "amount", "frequency", "next_date", "end_date", "active"]
        widgets = {"next_date": DateInput(), "end_date": DateInput()}


class SavingsGoalForm(UserModelForm):
    class Meta:
        model = SavingsGoal
        fields = ["name", "target_amount", "saved_so_far", "target_date"]
        widgets = {"target_date": DateInput()}


class ForecastForm(forms.Form):
    days = forms.TypedChoiceField(choices=DAY_CHOICES, coerce=int, initial=90, label="Horizon")
    daily_spend = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        label="Everyday spending per day (override)",
        help_text="Leave blank to use the estimate from your last 90 days.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class WhatIfForm(forms.Form):
    days = forms.TypedChoiceField(choices=DAY_CHOICES, coerce=int, initial=90, label="Horizon")
    purchase_amount = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2, label="One-off purchase"
    )
    purchase_date = forms.DateField(required=False, widget=DateInput(), label="Purchase date")
    monthly_income_change = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        label="Change in monthly income",
        help_text="Positive = raise, negative = loss. Applied monthly from next month.",
    )
    monthly_expense_cut = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
        label="Reduce monthly spending by",
        help_text="Lowers everyday spending by this amount per month.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean(self):
        data = super().clean()
        if data.get("purchase_amount") and not data.get("purchase_date"):
            self.add_error("purchase_date", "Choose when you would buy it.")
        if not any(data.get(k) for k in ("purchase_amount", "monthly_income_change", "monthly_expense_cut")):
            raise forms.ValidationError("Enter at least one change to simulate.")
        return data
