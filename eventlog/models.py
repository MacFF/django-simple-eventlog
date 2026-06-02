from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings

from eventlog.choices import EventLogAction

class EventLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        blank=False,
        null=True,
        related_name="actor_eventlogs",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    template_message = models.TextField(blank=False, null=False)

    object_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING)
    object_id = models.PositiveBigIntegerField(blank=False, null=True)
    object = GenericForeignKey("object_type", "object_id")

    tool = models.CharField(max_length=100)
    action = models.CharField(choices=EventLogAction.choices, max_length=50)
    changes = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Event Log'
        verbose_name_plural = 'Event Logs'

    def __str__(self):
        return f"{self.action} on {self.object_type} ({self.timestamp})"


class RelatedValueEventLog(models.Model):
    log = models.ForeignKey(EventLog, on_delete=models.PROTECT, related_name="related_values")

    text_format = models.TextField(blank=False, null=False)

    object_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING, blank=False, null=True)
    object_id = models.PositiveBigIntegerField(blank=False, null=True)
    object = GenericForeignKey("object_type", "object_id")

    default_value = models.TextField(default="")

    class Meta:
        verbose_name = 'Related Value Event Log'
        verbose_name_plural = 'Related Value Event Logs'

    def __str__(self):
        return f"{self.log_id} - {self.text_format}"
