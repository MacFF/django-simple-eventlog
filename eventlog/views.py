from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters import rest_framework as filters
from eventlog.models import EventLog
from eventlog.serializers import EventLogSerializer


class EventLogFilter(filters.FilterSet):
    class Meta:
        model = EventLog
        fields = ['tool', 'action', 'actor', 'object_id', 'object_type']


class EventLogViewSet(ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing event logs.
    """
    queryset = EventLog.objects.all().order_by("-timestamp")
    serializer_class = EventLogSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = EventLogFilter
