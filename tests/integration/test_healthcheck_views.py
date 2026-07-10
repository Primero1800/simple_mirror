"""Integration tests for the /api/health/ endpoint — admin-only DRF ViewSet.

HealthCheckService.check() is mocked throughout: the underlying db/qdrant
checks are exercised directly in tests/unit/test_health_check_service.py.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse

from healthcheck.exceptions import HealthCheckError

SERVICE = "healthcheck.views.HealthCheckService"


@pytest.mark.django_db
def test_anonymous_request_is_forbidden(client):
    response = client.get(reverse("health-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_user_is_forbidden(client, active_user):
    client.force_login(active_user)
    response = client.get(reverse("health-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_health_returns_200_when_all_components_healthy(admin_client):
    with patch(f"{SERVICE}.check", return_value=None):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_returns_503_with_detail_when_unhealthy(admin_client):
    with patch(f"{SERVICE}.check", side_effect=HealthCheckError("db: DB unreachable")):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["detail"] == "db: DB unreachable"
