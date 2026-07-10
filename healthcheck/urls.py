from rest_framework.routers import DefaultRouter

from healthcheck.views import HealthViewSet

router = DefaultRouter()
router.register("health", HealthViewSet, basename="health")

urlpatterns = router.urls
