"""Integration tests for the /api/health/ endpoint — admin-only DRF ViewSet.

HealthCheckService.check_db/check_qdrant are mocked throughout: there is no
real Qdrant instance in the test environment, and the db case is mocked too
so both branches are tested independently of what the real test DB reports.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse

from healthcheck.exceptions import DBHealthCheckError, QdrantHealthCheckError

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
    with (
        patch(f"{SERVICE}.check_db", return_value=None),
        patch(f"{SERVICE}.check_qdrant", return_value=None),
    ):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "db": "ok", "qdrant": "ok"}


@pytest.mark.django_db
def test_health_returns_503_when_db_unreachable(admin_client):
    with (
        patch(f"{SERVICE}.check_db", side_effect=DBHealthCheckError("DB unreachable")),
        patch(f"{SERVICE}.check_qdrant", return_value=None),
    ):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "DB unreachable"
    assert body["qdrant"] == "ok"


@pytest.mark.django_db
def test_health_returns_503_when_qdrant_unreachable(admin_client):
    with (
        patch(f"{SERVICE}.check_db", return_value=None),
        patch(
            f"{SERVICE}.check_qdrant",
            side_effect=QdrantHealthCheckError("Qdrant unreachable"),
        ),
    ):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "ok"
    assert body["qdrant"] == "Qdrant unreachable"


@pytest.mark.django_db
def test_health_returns_503_when_both_components_unreachable(admin_client):
    with (
        patch(f"{SERVICE}.check_db", side_effect=DBHealthCheckError("DB unreachable")),
        patch(
            f"{SERVICE}.check_qdrant",
            side_effect=QdrantHealthCheckError("Qdrant unreachable"),
        ),
    ):
        response = admin_client.get(reverse("health-list"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "DB unreachable"
    assert body["qdrant"] == "Qdrant unreachable"
