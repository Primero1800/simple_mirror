"""Unit tests for HealthCheckService — DB connection is mocked."""

import time

import pytest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.db import OperationalError

from healthcheck.exceptions import (
    DBHealthCheckError,
    HealthCheckError,
    QdrantHealthCheckError,
)
from healthcheck.services.health_check_service import HealthCheckService

SERVICE = "healthcheck.services.health_check_service"


def _mock_connection(cursor: MagicMock, vendor: str = "postgresql") -> MagicMock:
    """Build a mock `connection` whose cursor() context manager yields *cursor*."""
    conn = MagicMock()
    conn.vendor = vendor
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.cursor.return_value.__exit__.return_value = False
    return conn


class TestCheckDb:
    # transaction.atomic() is patched with a real nullcontext() rather than a
    # bare MagicMock — MagicMock's __exit__ is truthy by default and would
    # silently swallow the OperationalError raised inside, breaking retries.

    def test_succeeds_on_first_attempt(self):
        cursor = MagicMock()
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor)),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            HealthCheckService.check_db()  # must not raise

            assert cursor.execute.call_count == 2
            cursor.execute.assert_any_call("SELECT 1")

    def test_succeeds_after_transient_failure(self):
        cursor = MagicMock()
        cursor.execute.side_effect = [None, OperationalError("down"), None, None]
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor)),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            HealthCheckService.check_db()  # must not raise

    def test_raises_after_all_retries_exhausted(self):
        cursor = MagicMock()
        cursor.execute.side_effect = OperationalError("down")
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor)),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            with pytest.raises(DBHealthCheckError):
                HealthCheckService.check_db()

    def test_retries_exactly_three_times_before_raising(self):
        cursor = MagicMock()
        cursor.execute.side_effect = OperationalError("down")
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor)),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            with pytest.raises(DBHealthCheckError):
                HealthCheckService.check_db()
            # fails on the first statement (SET LOCAL) each attempt, so 1 call per attempt
            assert cursor.execute.call_count == 3

    def test_uses_configured_timeout_on_postgresql(self, settings):
        settings.HEALTH_CHECK_TIMEOUT_SEC = 2
        cursor = MagicMock()
        with (
            patch(
                f"{SERVICE}.connection", _mock_connection(cursor, vendor="postgresql")
            ),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            HealthCheckService.check_db()

            cursor.execute.assert_any_call("SET LOCAL statement_timeout = %s", [2000])

    def test_uses_configured_timeout_on_mysql(self, settings):
        settings.HEALTH_CHECK_TIMEOUT_SEC = 2
        cursor = MagicMock()
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor, vendor="mysql")),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            HealthCheckService.check_db()

            cursor.execute.assert_any_call(
                "SET SESSION MAX_EXECUTION_TIME = %s", [2000]
            )

    def test_skips_timeout_statement_on_unsupported_vendor(self):
        cursor = MagicMock()
        with (
            patch(f"{SERVICE}.connection", _mock_connection(cursor, vendor="sqlite")),
            patch(f"{SERVICE}.transaction.atomic", return_value=nullcontext()),
        ):
            HealthCheckService.check_db()  # must not raise

            cursor.execute.assert_called_once_with("SELECT 1")


class TestCheckQdrant:
    def test_passes_when_collection_exists(self):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True
        with (
            patch(f"{SERVICE}.get_qdrant_client", return_value=mock_client),
            patch(f"{SERVICE}.settings") as mock_settings,
        ):
            mock_settings.QDRANT_COLLECTION = "talks"

            HealthCheckService.check_qdrant()  # must not raise

            mock_client.collection_exists.assert_called_once_with("talks")

    def test_raises_when_collection_missing(self):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False
        with (
            patch(f"{SERVICE}.get_qdrant_client", return_value=mock_client),
            patch(f"{SERVICE}.settings") as mock_settings,
        ):
            mock_settings.QDRANT_COLLECTION = "talks"

            with pytest.raises(QdrantHealthCheckError, match="talks"):
                HealthCheckService.check_qdrant()

    def test_raises_when_client_unreachable(self):
        with patch(f"{SERVICE}.get_qdrant_client", side_effect=ConnectionError("down")):
            with pytest.raises(QdrantHealthCheckError):
                HealthCheckService.check_qdrant()


class TestCheck:
    """Tests for the check() orchestrator — db and qdrant run in parallel threads."""

    def test_passes_when_both_components_healthy(self):
        with (
            patch.object(HealthCheckService, "check_db", return_value=None),
            patch.object(HealthCheckService, "check_qdrant", return_value=None),
        ):
            HealthCheckService.check()  # must not raise

    def test_raises_with_db_detail_when_db_unhealthy(self):
        with (
            patch.object(
                HealthCheckService,
                "check_db",
                side_effect=DBHealthCheckError("DB unreachable"),
            ),
            patch.object(HealthCheckService, "check_qdrant", return_value=None),
        ):
            with pytest.raises(HealthCheckError, match="db: DB unreachable"):
                HealthCheckService.check()

    def test_raises_with_qdrant_detail_when_qdrant_unhealthy(self):
        with (
            patch.object(HealthCheckService, "check_db", return_value=None),
            patch.object(
                HealthCheckService,
                "check_qdrant",
                side_effect=QdrantHealthCheckError("Qdrant unreachable"),
            ),
        ):
            with pytest.raises(HealthCheckError, match="qdrant: Qdrant unreachable"):
                HealthCheckService.check()

    def test_raises_with_both_details_when_both_unhealthy(self):
        with (
            patch.object(
                HealthCheckService,
                "check_db",
                side_effect=DBHealthCheckError("DB unreachable"),
            ),
            patch.object(
                HealthCheckService,
                "check_qdrant",
                side_effect=QdrantHealthCheckError("Qdrant unreachable"),
            ),
        ):
            with pytest.raises(HealthCheckError) as exc_info:
                HealthCheckService.check()
            assert "db: DB unreachable" in str(exc_info.value)
            assert "qdrant: Qdrant unreachable" in str(exc_info.value)

    def test_raises_timeout_detail_when_a_check_hangs(self, settings):
        settings.HEALTH_CHECK_TIMEOUT_SEC = 0.05

        def _hang(*args: object, **kwargs: object) -> None:
            time.sleep(0.2)

        with (
            patch.object(HealthCheckService, "check_db", side_effect=_hang),
            patch.object(HealthCheckService, "check_qdrant", return_value=None),
        ):
            with pytest.raises(HealthCheckError, match="db: timeout"):
                HealthCheckService.check()
