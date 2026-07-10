import logging

from django.conf import settings
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Return the shared Qdrant client, creating it lazily on first use.

    Returns:
        Cached QdrantClient instance, configured from settings.
    """
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            check_compatibility=False,
            timeout=settings.QDRANT_TIMEOUT,
        )
        logger.debug("Qdrant client initialized.")
    return _client
