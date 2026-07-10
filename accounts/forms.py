from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _


class RegisterForm(forms.Form):
    """Registration form collecting email and a confirmed password."""

    email = forms.EmailField(label="Email")
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Пароль"),
        min_length=8,
        error_messages={"min_length": _("Пароль должен быть не менее 8 символов.")},
    )
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("Повторите пароль"))

    def clean_password(self) -> str:
        """Require at least one letter and one digit in the password.

        Returns:
            The validated password value.

        Raises:
            ValidationError: If the password contains no letters or no digits.
        """
        password: str = self.cleaned_data.get("password", "")
        if not any(c.isalpha() for c in password):
            raise forms.ValidationError(_("Пароль должен содержать хотя бы одну букву"))
        if not any(c.isdigit() for c in password):
            raise forms.ValidationError(_("Пароль должен содержать хотя бы одну цифру"))
        return password

    def clean(self) -> dict[str, Any]:
        """Validate that both password fields contain the same value.

        Returns:
            Cleaned data dictionary.

        Raises:
            ValidationError: If the two password fields do not match.
        """
        cd: dict[str, Any] = super().clean() or {}
        p1 = cd.get("password")
        p2 = cd.get("password2")
        if p1 is not None and p2 is not None and p1 != p2:
            raise forms.ValidationError(_("Пароли не совпадают"))
        return cd


class LoginForm(forms.Form):
    """Login form collecting email and password credentials."""

    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label=_("Пароль"))
