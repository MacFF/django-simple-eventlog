from string import Formatter

from rest_framework import serializers
from django.db.models import Model

from django_simple_eventlog.models import EventLog, RelatedValueEventLog


class EventLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.get_full_name", read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = EventLog
        exclude = ["template_message"]

    def get_message(self, instance):
        formatter = Formatter()
        format_dict_map = {}
        template_message = instance.template_message
        for _, text_format, _, _ in formatter.parse(template_message):
            if text_format is None:
                continue
            related_instance = RelatedValueEventLog.objects.filter(text_format=text_format, log=instance).first()
            if related_instance:
                realated_obj = related_instance.object
                list_attr = text_format.split("__")[1:]
                for attr in list_attr:
                    if hasattr(realated_obj, attr) == False:
                        break
                    realated_obj = getattr(realated_obj, attr, None)
                format_dict_map[text_format] = "" if isinstance(realated_obj, Model) else realated_obj
        return template_message.format(**format_dict_map) if format_dict_map else template_message
