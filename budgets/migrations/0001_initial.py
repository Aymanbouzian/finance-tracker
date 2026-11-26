from decimal import Decimal

import budgets.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("ledger", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="Budget",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(default=budgets.models.current_month, help_text="The month this spending limit applies to.")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to="ledger.category")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="budgets", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["category__name"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "category", "month"), name="unique_budget_per_user_category_month"),
                    models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="budget_amount_positive"),
                ],
            },
        ),
    ]
