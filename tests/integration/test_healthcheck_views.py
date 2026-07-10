"""Integration tests for the /health/ endpoint."""

import pytest
from unittest.mock import patch
from django.urls import reverse

from healthcheck.exceptions import DBHealthCheckError

VIEWS = "healthcheck.views"


@pytest.mark.django_db
def test_health_returns_200_when_db_reachable(client):
    response = client.get(reverse("healthcheck:health"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_health_returns_503_when_db_unreachable(client):
    with patch(
        f"{VIEWS}.HealthCheckService.check_db",
        side_effect=DBHealthCheckError("DB unreachable"),
    ):
        response = client.get(reverse("healthcheck:health"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["db"] == "DB unreachable"
