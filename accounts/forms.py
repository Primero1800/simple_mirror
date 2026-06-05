from typing import Any

from django import forms


class RegisterForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Password', min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, label='Repeat password')

    def clean(self) -> dict[str, Any]:
        """Validate that both password fields match."""
        cd: dict[str, Any] = super().clean() or {}
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match')
        return cd


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
