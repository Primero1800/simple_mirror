from django.utils.translation import gettext_lazy as _


class AccountsError(Exception):
    """Base exception for the accounts domain."""


class UserAlreadyExistsError(AccountsError):
    """Raised when attempting to register an email that belongs to an active account."""


class EmailDeliveryError(AccountsError):
    """Raised when an OTP email cannot be delivered after all retry attempts."""


class OTPBlockedError(AccountsError):
    """Raised when an email is temporarily blocked due to too many failed OTP attempts."""


class OTPCooldownError(AccountsError):
    """Raised when a new OTP cannot be sent because the resend cooldown is still active.

    Attributes:
        seconds_remaining: Seconds until the cooldown expires.
    """

    def __init__(self, seconds_remaining: int) -> None:
        self.seconds_remaining = seconds_remaining
        super().__init__(
            _('Повторите отправку через %(sec)s сек.') % {'sec': seconds_remaining}
        )
