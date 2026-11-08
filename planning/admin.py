from django.contrib import admin

from .models import RecurringItem, SavingsGoal


@admin.register(RecurringItem)
class RecurringItemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "amount", "frequency", "next_date", "active", "user")
    list_filter = ("kind", "frequency", "active")


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ("name", "target_amount", "saved_so_far", "target_date", "user")
