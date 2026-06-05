import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from accounts.models import OTPCode, User
from accounts.repositories.otp_repo import OTPRepository
from accounts.repositories.user_repo import UserRepository
from accounts.services.email_service import EmailService


class AuthService:
    """Business logic layer for authentication and registration flows."""

    @staticmethod
    def _create_otp(user: User) -> OTPCode:
        """Enforce the "one active OTP per user" rule and generate a new code.

        Must be called inside an active transaction so that deletion and
        creation are atomic.

        Args:
            user: The user for whom the OTP is being created.

        Returns:
            Freshly persisted OTPCode instance.
        """
        # 1. Invalidate all previous codes for this user
        OTPRepository.delete_for_user(user)
        # 2. Generate a cryptographically secure 4-digit code
        code = f'{secrets.randbelow(10000):04d}'
        # 3. Compute expiry timestamp from settings
        lifetime: int = getattr(settings, 'OTP_LIFETIME_SECONDS', 60)
        expires_at = datetime.now() + timedelta(seconds=lifetime)
        # 4. Persist and return the new record
        return OTPRepository.create(user=user, code=code, expires_at=expires_at)

    @staticmethod
    def register(email: str, password: str) -> User:
        """Register a new user and trigger OTP email delivery.

        If an *inactive* account with the same email already exists (e.g. a
        previous registration where delivery failed), it is atomically replaced.

        Args:
            email: New user's email address.
            password: Plain-text password (hashed before storage).

        Returns:
            Newly created, inactive User.

        Raises:
            ValueError: If an *active* account with *email* already exists.
        """
        # 1. Open an atomic block covering all DB writes
        with transaction.atomic():
            # 2. Handle duplicate email: reject active, replace inactive
            existing = UserRepository.get_by_email(email)
            if existing is not None:
                if existing.is_active:
                    raise ValueError('A user with this email already exists')
                existing.delete()  # cascades to OTPCode rows

            # 3. Create inactive user and fresh OTP
            user = UserRepository.create(email=email, password=password, is_active=False)
            otp = AuthService._create_otp(user)

        # 4. Dispatch email outside the transaction (non-blocking)
        EmailService.send_otp_async(email=user.email, code=otp.code)
        return user

    @staticmethod
    def send_otp(user: User) -> None:
        """Create a fresh OTP for *user* and dispatch it by email asynchronously.

        Used for both the login second-factor step and the resend flow.

        Args:
            user: The user who needs a new OTP.
        """
        with transaction.atomic():
            otp = AuthService._create_otp(user)
        EmailService.send_otp_async(email=user.email, code=otp.code)

    @staticmethod
    def verify_otp(user: User, code: str) -> bool:
        """Validate the submitted OTP against the stored record.

        Args:
            user: Owner of the OTP.
            code: 4-digit string submitted by the user.

        Returns:
            True if the code matches and has not expired; False otherwise.
        """
        otp = OTPRepository.get_latest(user)
        if not otp or not otp.is_valid():
            return False
        if otp.code != code:
            return False
        OTPRepository.delete(otp)
        return True

    @staticmethod
    def get_user_by_id(pk: int) -> User | None:
        """Resolve a user by primary key.

        Args:
            pk: User primary key (typically read from session).

        Returns:
            Matching User or None.
        """
        return UserRepository.get_by_id(pk)

    @staticmethod
    def get_seconds_remaining(user: User) -> int:
        """Return seconds until the user's current OTP expires, or 0 if none.

        Args:
            user: Owner of the OTP.

        Returns:
            Non-negative integer seconds remaining.
        """
        otp = OTPRepository.get_latest(user)
        if not otp:
            return 0
        return max(0, int((datetime.now() - otp.expires_at).total_seconds() * -1))

    @staticmethod
    def activate(user: User) -> User:
        """Mark a user account as active after successful OTP verification.

        Args:
            user: User to activate.

        Returns:
            Saved User instance.
        """
        user.is_active = True
        return UserRepository.save(user)

    @staticmethod
    def authenticate(email: str, password: str) -> User | None:
        """Verify email/password credentials.

        Args:
            email: Candidate email address.
            password: Plain-text password to check.

        Returns:
            The User when credentials are valid and the account is active;
            None otherwise.
        """
        user = UserRepository.get_by_email(email)
        if user and user.check_password(password) and user.is_active:
            return user
        return None
