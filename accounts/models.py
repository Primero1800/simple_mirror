from datetime import datetime
from typing import ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Custom manager that uses email as the unique identifier instead of username."""

    def create_user(
        self, email: str, password: str | None = None, **extra: object
    ) -> "User":
        """Create and persist a regular user account.

        Args:
            email: User's email address; used as the login identifier.
            password: Plain-text password; stored as a hash.
            **extra: Additional field values passed to the model constructor.

        Returns:
            Saved User instance.

        Raises:
            ValueError: If *email* is empty or not provided.
        """
        # 1. Reject blank email early to give a clear error message
        if not email:
            raise ValueError("Email is required")
        # 2. Normalise the domain part of the email (lowercased)
        user = self.model(email=self.normalize_email(email), **extra)
        # 3. Hash the password before storing
        user.set_password(password)
        # 4. Persist the new record to the database
        user.save(using=self._db)
        return user  # type: ignore[return-value]

    def create_superuser(
        self, email: str, password: str | None = None, **extra: object
    ) -> "User":
        """Create a superuser with staff and superuser flags set by default.

        Args:
            email: User's email address.
            password: Plain-text password.
            **extra: Additional field values; is_staff/is_superuser/is_active default to True.

        Returns:
            Saved superuser instance.
        """
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    """Application user model with email as the primary login identifier."""

    username = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []
    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    def __str__(self) -> str:
        return self.email


class OTPCode(models.Model):
    """One-time password code tied to a user with an explicit expiry timestamp."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otp_codes",
    )
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self) -> bool:
        """Return True if the code has not yet expired."""
        return datetime.now() < self.expires_at
