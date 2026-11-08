from django.contrib.auth.mixins import LoginRequiredMixin


class UserQuerysetMixin(LoginRequiredMixin):
    """Restrict a view's queryset to objects owned by the logged-in user."""

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class UserFormMixin:
    """Pass the logged-in user to forms that scope their choices to that user."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
