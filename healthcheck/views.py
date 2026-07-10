from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from healthcheck.exceptions import DBHealthCheckError
from healthcheck.services.health_check_service import HealthCheckService


class HealthViewSet(viewsets.ViewSet):
    """Infrastructure health status endpoint.

    Permission:
        IsAdminUser: only staff accounts may query health status.
    """

    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        """Return infrastructure health status.

        Returns 200 if all components are healthy, 503 otherwise.

        Args:
            request: DRF request.

        Returns:
            Response with component statuses.
        """
        checks: dict[str, str] = {}
        ok = True

        try:
            HealthCheckService.check_db()
            checks["db"] = "ok"
        except DBHealthCheckError as exc:
            checks["db"] = str(exc)
            ok = False

        return Response(
            {"status": "ok" if ok else "error", **checks},
            status=200 if ok else 503,
        )
