from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType

from eventlog.models import EventLog
from eventlog.serializers import EventLogSerializer


class EventLogMixin:
    """
    A viewset mixin that adds a `/log/` endpoint to retrieve event logs 
    for the specific object instance.
    """

    @action(
        methods=["GET"],
        detail=True,
        url_path="log",
        serializer_class=EventLogSerializer,
    )
    def log_detail(self, request, *args, **kwargs):
        instance = self.get_object()
        ct = ContentType.objects.get_for_model(instance, for_concrete_model=False)
        event_logs = EventLog.objects.filter(object_type=ct, object_id=instance.pk).order_by("-timestamp")

        page = self.paginate_queryset(event_logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(event_logs, many=True)
        return Response(serializer.data)
