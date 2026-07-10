class HealthCheckError(Exception):
    """Base class for health check failures."""


class DBHealthCheckError(HealthCheckError):
    """Raised when the database is unreachable or returns an error."""


class QdrantHealthCheckError(HealthCheckError):
    """Raised when Qdrant is unreachable or the collection does not exist."""
