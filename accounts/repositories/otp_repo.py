from datetime import datetime

from accounts.models import OTPCode, User


class OTPRepository:
    """Data-access layer for OTPCode records.

    Each method performs a single, focused database operation.
    Business rules (e.g. "one OTP per user") live in the service layer.
    """

    @staticmethod
    def delete_for_user(user: User) -> None:
        """Delete all OTP codes that belong to *user*.

        Args:
            user: The owner whose codes should be removed.
        """
        OTPCode.objects.filter(user=user).delete()

    @staticmethod
    def create(user: User, code: str, expires_at: datetime) -> OTPCode:
        """Persist a new OTP code record.

        Args:
            user: Owner of the code.
            code: 4-digit string.
            expires_at: Naive datetime after which the code is invalid.

        Returns:
            Saved OTPCode instance.
        """
        return OTPCode.objects.create(user=user, code=code, expires_at=expires_at)

    @staticmethod
    def get_latest(user: User) -> OTPCode | None:
        """Return the most recently created OTP for *user*, or None.

        Args:
            user: Owner to query.

        Returns:
            Latest OTPCode or None if no records exist.
        """
        return OTPCode.objects.filter(user=user).order_by("-created_at").first()

    @staticmethod
    def delete(otp: OTPCode) -> None:
        """Delete a single OTP code record.

        Args:
            otp: The record to remove.
        """
        otp.delete()
