from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from ledger.models import MONEY, Category, Transaction


def current_month():
    return timezone.localdate().replace(day=1)


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    month = models.DateField(default=current_month, help_text="The month this spending limit applies to.")
    amount = models.DecimalField(validators=[MinValueValidator(Decimal("0.01"))], **MONEY)

    class Meta:
        ordering = ["category__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "category", "month"], name="unique_budget_per_user_category_month"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="budget_amount_positive"),
        ]

    def __str__(self):
        return f"{self.category} · {self.month:%B %Y}"

    def clean(self):
        super().clean()
        if self.month:
            self.month = self.month.replace(day=1)
        if self.category_id:
            if self.category.kind != Transaction.EXPENSE:
                raise ValidationError({"category": "Choose an expense category."})
            if self.user_id and self.category.user_id != self.user_id:
                raise ValidationError({"category": "Choose one of your own categories."})

    def save(self, *args, **kwargs):
        # Preserve normalization and ownership even outside the user-facing form.
        self.full_clean()
        return super().save(*args, **kwargs)
