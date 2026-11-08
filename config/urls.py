from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from ledger.forms import StyledAuthenticationForm
from ledger.views import register

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(authentication_form=StyledAuthenticationForm),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("register/", register, name="register"),
    path("planning/", include("planning.urls")),
    path("", include("ledger.urls")),
]
