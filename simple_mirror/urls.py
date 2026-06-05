from django.http import HttpResponse
from django.urls import include, path


def _favicon(_request: object) -> HttpResponse:
    return HttpResponse(status=204)


urlpatterns = [
    path('favicon.ico', _favicon),
    path('accounts/', include('accounts.urls')),
    path('', include('mirror.urls')),
]
