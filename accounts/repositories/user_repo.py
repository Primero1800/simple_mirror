from accounts.models import User


class UserRepository:
    """Data-access layer for User records."""

    @staticmethod
    def get_by_email(email: str) -> User | None:
        """Fetch a user by email address.

        Args:
            email: Exact email to look up.

        Returns:
            Matching User or None.
        """
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_id(pk: int) -> User | None:
        """Fetch a user by primary key.

        Args:
            pk: User primary key.

        Returns:
            Matching User or None.
        """
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    @staticmethod
    def create(email: str, password: str, is_active: bool = True) -> User:
        """Create and persist a new user.

        Args:
            email: User's email address (used as username).
            password: Plain-text password; stored as a hash.
            is_active: Whether the account is immediately usable.

        Returns:
            Saved User instance.
        """
        return User.objects.create_user(  # type: ignore[return-value]
            email=email, password=password, is_active=is_active
        )

    @staticmethod
    def save(user: User) -> User:
        """Persist changes to an existing user instance.

        Args:
            user: User with modified fields.

        Returns:
            The same User after save().
        """
        user.save()
        return user
