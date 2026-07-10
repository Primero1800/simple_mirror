"""Integration tests for the /api/health/ endpoint — admin-only DRF view."""

import pytest
from unittest.mock import patch
from django.urls import reverse

from healthcheck.exceptions import DBHealthCheckError

VIEWS = "healthcheck.views"


@pytest.mark.django_db
def test_anonymous_request_is_forbidden(client):
    response = client.get(reverse("healthcheck:health"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_user_is_forbidden(client, active_user):
    client.force_login(active_user)
    response = client.get(reverse("healthcheck:health"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_health_returns_200_when_db_reachable(admin_client):
    response = admin_client.get(reverse("healthcheck:health"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_health_returns_503_when_db_unreachable(admin_client, db):
    with patch(
        f"{VIEWS}.HealthCheckService.check_db",
        side_effect=DBHealthCheckError("DB unreachable"),
    ):
        response = admin_client.get(reverse("healthcheck:health"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "DB unreachable"
