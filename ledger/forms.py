from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Account, Category, Transaction

MAX_IMPORT_BYTES = 2 * 1024 * 1024


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)


def style_fields(form):
    """Add Bootstrap classes to every widget of a form."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            css = "form-select"
        else:
            css = "form-control"
        widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class UserModelForm(forms.ModelForm):
    """ModelForm bound to a user: the user is set on the instance, never taken from input."""

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user
        style_fields(self)


class AccountForm(UserModelForm):
    class Meta:
        model = Account
        fields = ["name", "opening_balance"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        clash = Account.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("You already have an account with this name.")
        return name


class CategoryForm(UserModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        clash = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("You already have a category with this name.")
        return name


class TransactionForm(UserModelForm):
    class Meta:
        model = Transaction
        fields = ["kind", "account", "to_account", "amount", "date", "category", "description"]
        widgets = {"date": DateInput()}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, user=user, **kwargs)
        accounts = Account.objects.filter(user=user)
        self.fields["account"].queryset = accounts
        self.fields["to_account"].queryset = accounts
        self.fields["category"].queryset = Category.objects.filter(user=user)


class CSVImportForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none())
    file = forms.FileField(
        label="CSV file",
        help_text="Columns: date, amount, description (+ optional category). Negative amount = expense.",
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user=user)
        style_fields(self)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > MAX_IMPORT_BYTES:
            raise forms.ValidationError("File is too large (max 2 MB).")
        try:
            # Returns the decoded text, not the upload object.
            return upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise forms.ValidationError("The file must be UTF-8 encoded text.")


class RegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
