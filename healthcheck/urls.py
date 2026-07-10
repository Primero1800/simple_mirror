from django.urls import path

from healthcheck.views import HealthView

app_name = "healthcheck"

urlpatterns = [
    path("", HealthView.as_view(), name="health"),
]
