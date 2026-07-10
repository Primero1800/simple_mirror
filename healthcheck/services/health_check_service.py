import logging

from django.conf import settings
from django.db import OperationalError, connection, transaction

from healthcheck.exceptions import DBHealthCheckError

logger = logging.getLogger(__name__)

_RETRIES = 3


class HealthCheckService:
    @staticmethod
    def check_db() -> None:
        """Check database connectivity with timeout and retries.

        Executes SELECT 1 with a statement-level timeout. Retries up to
        _RETRIES times before raising.

        Raises:
            DBHealthCheckError: if the database is unreachable after all retries.
        """
        timeout_ms = settings.HEALTH_CHECK_TIMEOUT_SEC * 1000
        last_exc: Exception | None = None

        for attempt in range(1, _RETRIES + 1):
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL statement_timeout = %s", [timeout_ms])
                        cursor.execute("SELECT 1")
                return
            except OperationalError as exc:
                last_exc = exc
                logger.warning(
                    "DB health check attempt %d/%d failed",
                    attempt,
                    _RETRIES,
                    exc_info=exc,
                )

        logger.critical(
            "DB health check failed after %d attempts", _RETRIES, exc_info=last_exc
        )
        raise DBHealthCheckError("DB unreachable") from last_exc
