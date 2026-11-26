from django.urls import path

from . import views

app_name = "clientapi"
urlpatterns = [
    path("session/", views.session, name="session"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("overview/", views.overview, name="overview"),
    path("forecast/", views.forecast, name="forecast"),
    path("what-if/", views.what_if, name="what-if"),
    path("assistant/", views.assistant, name="assistant"),
    path("export/", views.export, name="export"),
    path("import/", views.import_file, name="import"),
    path("<str:resource>/", views.collection, name="collection"),
    path("<str:resource>/<int:pk>/", views.detail, name="detail"),
    path("<path:unknown>", views.not_found),
]
