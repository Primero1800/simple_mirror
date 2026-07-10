import atexit
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from django.conf import settings
from django.db import OperationalError, connection, transaction

from healthcheck.exceptions import (
    DBHealthCheckError,
    HealthCheckError,
    QdrantHealthCheckError,
)
from simple_mirror.infrastructure.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

_RETRIES = 3
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared thread-pool, creating it lazily on first use."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2)
    return _executor


def _shutdown_executor() -> None:
    """Drain the pool on process exit."""
    if _executor is not None:
        _executor.shutdown(wait=False)


atexit.register(_shutdown_executor)


class HealthCheckService:
    @staticmethod
    def check() -> None:
        """Run all infrastructure checks in parallel.

        Raises:
            HealthCheckError: if any component is unhealthy or times out.
        """
        timeout = settings.HEALTH_CHECK_TIMEOUT_SEC
        executor = _get_executor()
        errors: list[str] = []

        futures = {
            "db": executor.submit(HealthCheckService.check_db),
            "qdrant": executor.submit(HealthCheckService.check_qdrant),
        }
        for key, future in futures.items():
            try:
                future.result(timeout=timeout)
            except FutureTimeout:
                errors.append(f"{key}: timeout")
            except (DBHealthCheckError, QdrantHealthCheckError) as exc:
                errors.append(f"{key}: {exc}")

        if errors:
            raise HealthCheckError("; ".join(errors))

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
                        if connection.vendor == "postgresql":
                            cursor.execute(
                                "SET LOCAL statement_timeout = %s", [timeout_ms]
                            )
                        elif connection.vendor == "mysql":
                            cursor.execute(
                                "SET SESSION MAX_EXECUTION_TIME = %s", [timeout_ms]
                            )
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

    @staticmethod
    def check_qdrant() -> None:
        """Check Qdrant connectivity by verifying the collection exists.

        Raises:
            QdrantHealthCheckError: if Qdrant is unreachable or the collection is missing.
        """
        try:
            exists = get_qdrant_client().collection_exists(settings.QDRANT_COLLECTION)
        except Exception as exc:
            logger.critical("Qdrant health check failed", exc_info=exc)
            raise QdrantHealthCheckError("Qdrant unreachable") from exc
        if not exists:
            raise QdrantHealthCheckError(
                f"Collection '{settings.QDRANT_COLLECTION}' not found"
            )
