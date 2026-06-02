from rest_framework.routers import DefaultRouter
from django_simple_eventlog.views import EventLogViewSet

router = DefaultRouter()
router.register(r'eventlogs', EventLogViewSet, basename='eventlog')

urlpatterns = router.urls
