from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

MONEY = {"max_digits": 12, "decimal_places": 2}
ZERO = Decimal("0.00")


def _total(queryset):
    return queryset.aggregate(total=Sum("amount"))["total"] or ZERO


class Account(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=100)
    opening_balance = models.DecimalField(default=ZERO, **MONEY)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_account_name_per_user"),
        ]

    def __str__(self):
        return self.name

    @property
    def balance(self):
        """Opening balance + income - expenses - transfers out + transfers in."""
        own = self.transactions
        return (
            self.opening_balance
            + _total(own.filter(kind=Transaction.INCOME))
            - _total(own.filter(kind=Transaction.EXPENSE))
            - _total(own.filter(kind=Transaction.TRANSFER))
            + _total(self.incoming_transfers.all())
        )


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=10, choices=[("income", "Income"), ("expense", "Expense")])

    class Meta:
        ordering = ["kind", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_category_name_per_user"),
        ]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    KINDS = [(INCOME, "Income"), (EXPENSE, "Expense"), (TRANSFER, "Transfer")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    to_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="incoming_transfers",
        help_text="Only for transfers between your own accounts.",
    )
    kind = models.CharField(max_length=10, choices=KINDS)
    amount = models.DecimalField(validators=[MinValueValidator(Decimal("0.01"))], **MONEY)
    date = models.DateField(default=timezone.localdate)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} on {self.date}"

    def clean(self):
        errors = {}
        if self.kind == self.TRANSFER:
            self.category = None
            if not self.to_account_id:
                errors["to_account"] = "Choose the destination account for a transfer."
            elif self.to_account_id == self.account_id:
                errors["to_account"] = "The destination must be a different account."
        else:
            self.to_account = None
            if self.category_id and self.category.kind != self.kind:
                errors["category"] = "This category does not match the transaction type."

        if self.user_id:
            if self.account_id and self.account.user_id != self.user_id:
                errors["account"] = "Invalid account."
            if self.to_account_id and self.to_account.user_id != self.user_id:
                errors["to_account"] = "Invalid account."
            if self.category_id and self.category.user_id != self.user_id:
                errors["category"] = "Invalid category."

        if errors:
            raise ValidationError(errors)
