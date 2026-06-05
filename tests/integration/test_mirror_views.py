"""Integration tests for the mirror (webcam) page."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_index_returns_200(client):
    response = client.get(reverse('mirror:index'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_index_uses_correct_template(client):
    response = client.get(reverse('mirror:index'))
    assert 'mirror/index.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_nonexistent_url_returns_404(client):
    response = client.get('/nonexistent/')
    assert response.status_code == 404
