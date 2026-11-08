from django.urls import path

from . import views

urlpatterns = [
    path("forecast/", views.forecast_view, name="forecast"),
    path("what-if/", views.what_if_view, name="what-if"),
    path("goals/", views.goal_list, name="goal-list"),
    path("goals/new/", views.GoalCreate.as_view(), name="goal-create"),
    path("goals/<int:pk>/edit/", views.GoalUpdate.as_view(), name="goal-update"),
    path("goals/<int:pk>/delete/", views.GoalDelete.as_view(), name="goal-delete"),
    path("recurring/", views.RecurringList.as_view(), name="recurring-list"),
    path("recurring/new/", views.RecurringCreate.as_view(), name="recurring-create"),
    path("recurring/<int:pk>/edit/", views.RecurringUpdate.as_view(), name="recurring-update"),
    path("recurring/<int:pk>/delete/", views.RecurringDelete.as_view(), name="recurring-delete"),
]
