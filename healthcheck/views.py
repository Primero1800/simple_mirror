from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from healthcheck.exceptions import HealthCheckError
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
            Response with status and error detail if unhealthy.
        """
        try:
            HealthCheckService.check()
            return Response({"status": "ok"}, status=200)
        except HealthCheckError as exc:
            return Response({"status": "error", "detail": str(exc)}, status=503)
