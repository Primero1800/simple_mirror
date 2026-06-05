from django.test import Client
from django.urls import reverse


def test_index_returns_200(client: Client) -> None:
    response = client.get(reverse('mirror:index'))
    assert response.status_code == 200


def test_index_uses_template(client: Client) -> None:
    response = client.get(reverse('mirror:index'))
    assert 'mirror/index.html' in [t.name for t in response.templates]


def test_nonexistent_url_returns_404(client: Client) -> None:
    response = client.get('/nonexistent/')
    assert response.status_code == 404
