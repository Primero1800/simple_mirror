"""Unit tests for RegisterForm and LoginForm."""

from accounts.forms import LoginForm, RegisterForm


class TestRegisterForm:
    def test_valid_data_passes(self):
        form = RegisterForm(data={
            'email': 'user@example.com',
            'password': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
        })
        assert form.is_valid()

    def test_password_mismatch_raises_error(self):
        form = RegisterForm(data={
            'email': 'user@example.com',
            'password': 'Str0ngPass!',
            'password2': 'Different1!',
        })
        assert not form.is_valid()
        assert 'do not match' in str(form.errors).lower()

    def test_password_too_short_fails(self):
        form = RegisterForm(data={
            'email': 'user@example.com',
            'password': 'short',
            'password2': 'short',
        })
        assert not form.is_valid()

    def test_invalid_email_fails(self):
        form = RegisterForm(data={
            'email': 'not-an-email',
            'password': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
        })
        assert not form.is_valid()

    def test_missing_fields_fail(self):
        form = RegisterForm(data={})
        assert not form.is_valid()
        assert len(form.errors) > 0


class TestLoginForm:
    def test_valid_data_passes(self):
        form = LoginForm(data={'email': 'user@example.com', 'password': 'anypass'})
        assert form.is_valid()

    def test_invalid_email_fails(self):
        form = LoginForm(data={'email': 'bad', 'password': 'anypass'})
        assert not form.is_valid()

    def test_missing_password_fails(self):
        form = LoginForm(data={'email': 'user@example.com'})
        assert not form.is_valid()
