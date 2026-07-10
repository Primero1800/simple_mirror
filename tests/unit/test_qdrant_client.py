"""Unit tests for get_qdrant_client — QdrantClient constructor is mocked."""

from unittest.mock import patch

import simple_mirror.infrastructure.qdrant_client as qdrant_client_module
from simple_mirror.infrastructure.qdrant_client import get_qdrant_client

MODULE = "simple_mirror.infrastructure.qdrant_client"


def _reset_singleton() -> None:
    qdrant_client_module._client = None


class TestGetQdrantClient:
    def setup_method(self) -> None:
        _reset_singleton()

    def teardown_method(self) -> None:
        _reset_singleton()

    def test_creates_client_from_settings(self, settings):
        settings.QDRANT_URL = "https://example.qdrant.io:6333"
        settings.QDRANT_API_KEY = "secret-key"
        settings.QDRANT_TIMEOUT = 30
        with patch(f"{MODULE}.QdrantClient") as mock_cls:
            get_qdrant_client()

            mock_cls.assert_called_once_with(
                url="https://example.qdrant.io:6333",
                api_key="secret-key",
                check_compatibility=False,
                timeout=30,
            )

    def test_returns_cached_instance_on_subsequent_calls(self):
        with patch(f"{MODULE}.QdrantClient") as mock_cls:
            first = get_qdrant_client()
            second = get_qdrant_client()

            assert first is second
            mock_cls.assert_called_once()
