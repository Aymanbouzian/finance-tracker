from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from ledger.models import MONEY, Transaction


class RecurringItem(models.Model):
    MONTHLY = "monthly"
    WEEKLY = "weekly"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_items")
    name = models.CharField(max_length=100)
    kind = models.CharField(
        max_length=10,
        choices=[(Transaction.INCOME, "Income"), (Transaction.EXPENSE, "Expense / bill")],
    )
    amount = models.DecimalField(validators=[MinValueValidator(Decimal("0.01"))], **MONEY)
    frequency = models.CharField(max_length=10, choices=[(MONTHLY, "Monthly"), (WEEKLY, "Weekly")], default=MONTHLY)
    next_date = models.DateField(help_text="Any upcoming due date. Later ones are derived from it.")
    end_date = models.DateField(null=True, blank=True, help_text="Optional: the last possible date.")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.end_date and self.next_date and self.end_date < self.next_date:
            raise ValidationError({"end_date": "The end date cannot be before the next date."})


class SavingsGoal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals")
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(validators=[MinValueValidator(Decimal("0.01"))], **MONEY)
    saved_so_far = models.DecimalField(default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))], **MONEY)
    target_date = models.DateField()

    class Meta:
        ordering = ["target_date", "name"]

    def __str__(self):
        return self.name

    @property
    def remaining(self):
        return max(self.target_amount - self.saved_so_far, Decimal("0.00"))
