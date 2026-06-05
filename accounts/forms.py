from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _


class RegisterForm(forms.Form):
    """Registration form collecting email and a confirmed password."""

    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label=_('Пароль'), min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, label=_('Повторите пароль'))

    def clean(self) -> dict[str, Any]:
        """Validate that both password fields contain the same value.

        Returns:
            Cleaned data dictionary.

        Raises:
            ValidationError: If the two password fields do not match.
        """
        cd: dict[str, Any] = super().clean() or {}
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError(_('Пароли не совпадают'))
        return cd


class LoginForm(forms.Form):
    """Login form collecting email and password credentials."""

    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label=_('Пароль'))
