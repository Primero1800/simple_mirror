class HealthCheckError(Exception):
    """Base class for health check failures."""


class DBHealthCheckError(HealthCheckError):
    """Raised when the database is unreachable or returns an error."""
