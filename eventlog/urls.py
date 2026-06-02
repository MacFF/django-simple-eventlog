from rest_framework.routers import DefaultRouter
from eventlog.views import EventLogViewSet

router = DefaultRouter()
router.register(r'eventlogs', EventLogViewSet, basename='eventlog')

urlpatterns = router.urls
