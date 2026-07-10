from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def _favicon(_request: object) -> HttpResponse:
    return HttpResponse(status=204)


urlpatterns = [
    path("favicon.ico", _favicon),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

urlpatterns += i18n_patterns(
    path("accounts/", include("accounts.urls")),
    path("", include("mirror.urls")),
)
