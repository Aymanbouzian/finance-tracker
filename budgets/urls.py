from django.urls import path

from . import views

urlpatterns = [
    path("", views.budget_list, name="budget-list"),
    path("new/", views.BudgetCreate.as_view(), name="budget-create"),
    path("<int:pk>/edit/", views.BudgetUpdate.as_view(), name="budget-update"),
    path("<int:pk>/delete/", views.BudgetDelete.as_view(), name="budget-delete"),
]
