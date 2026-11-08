from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/", views.AccountList.as_view(), name="account-list"),
    path("accounts/new/", views.AccountCreate.as_view(), name="account-create"),
    path("accounts/<int:pk>/edit/", views.AccountUpdate.as_view(), name="account-update"),
    path("accounts/<int:pk>/delete/", views.AccountDelete.as_view(), name="account-delete"),
    path("categories/", views.CategoryList.as_view(), name="category-list"),
    path("categories/new/", views.CategoryCreate.as_view(), name="category-create"),
    path("categories/<int:pk>/delete/", views.CategoryDelete.as_view(), name="category-delete"),
    path("transactions/", views.TransactionList.as_view(), name="transaction-list"),
    path("transactions/new/", views.TransactionCreate.as_view(), name="transaction-create"),
    path("transactions/<int:pk>/edit/", views.TransactionUpdate.as_view(), name="transaction-update"),
    path("transactions/<int:pk>/delete/", views.TransactionDelete.as_view(), name="transaction-delete"),
    path("transactions/import/", views.import_csv, name="import-csv"),
    path("transactions/export/", views.export_csv, name="export-csv"),
]
