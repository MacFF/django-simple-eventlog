from string import Formatter
from typing import Any, Dict, List, Union
from rest_framework.exceptions import ValidationError

from django.db import models

from django_simple_eventlog.models import EventLog, RelatedValueEventLog

JSON = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

class EventLogService:

    @classmethod
    def log(cls, template_message, object, actor, tool, action, values_json: dict = None, changes=None):
        if values_json is None:
            values_json = {}

        has_text_format = False
        default_value_related = ""
        # ----------------------- validate format string -----------------------
        list_text_format_check = []
        formatter = Formatter()
        for literal_text, text_format, format_spec, conversion in formatter.parse(template_message):
            if text_format is None:
                continue
            if text_format in list_text_format_check:
                raise ValidationError({"log": f"Duplicate format string in 'template_message'"})
            list_text_format_check.append(text_format)
            value_or_instance = values_json.get(text_format, None)
            if value_or_instance is None:
                raise ValidationError({"log": f"Format string {text_format} is missing from 'values_json'"})
            if isinstance(value_or_instance, models.Model):
                validate_instance = value_or_instance
                list_attr = text_format.split("__")[1:]
                attr = ""
                for attr in list_attr:
                    if not hasattr(validate_instance, attr):
                        raise ValidationError({"log": f"Format string '{text_format}' of Model {value_or_instance.__class__.__name__} does not have attribute {attr}"})
                    validate_instance = getattr(validate_instance, attr, None)
                if attr:
                    default_value_related = str(getattr(value_or_instance, attr, ""))
                has_text_format = True
            if not isinstance(value_or_instance, models.Model):
                template_message = template_message.replace(f"{{{text_format}}}", str(value_or_instance))
        # --------------------------------------------------------------------
        event_log = EventLog.objects.create(
            template_message=template_message,
            object=object,
            actor=actor,
            tool=tool,
            action=action,
            changes=changes,
        )
        if has_text_format:
            for _, text_format, _, _ in formatter.parse(template_message):
                if text_format is None:
                    continue
                obj = values_json.get(text_format, None)

                RelatedValueEventLog.objects.create(
                    log=event_log, text_format=text_format, object=obj, default_value=default_value_related
                )

    @classmethod
    def create_diff_schema(cls, old_data, new_data, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = []
            
        exclude_keys = set(exclude_keys) | {
            "id",
            "created_at",
            "created_by",
            "updated_by",
            "updated_at",
            "uuid",
            "url",
        }

        def normalize_lists_to_dicts(data):
            """Convert list of dicts with id/uuid/document_type to dict keyed by it."""
            if isinstance(data, list):
                if all(isinstance(i, dict) for i in data):
                    keyed = {}
                    for item in data:
                        key = (
                            item.get("id")
                            or item.get("uuid")
                            or item.get("document_type")
                        )
                        if key is not None:
                            keyed[key] = normalize_lists_to_dicts(item)
                        else:
                            keyed[str(hash(str(item)))] = normalize_lists_to_dicts(item)
                    return keyed
                else:
                    return data[:]  # primitive list, keep as-is
            elif isinstance(data, dict):
                return {
                    k: normalize_lists_to_dicts(v)
                    for k, v in data.items()
                    if k not in exclude_keys
                }
            else:
                return data

        old_data = normalize_lists_to_dicts(old_data)
        new_data = normalize_lists_to_dicts(new_data)

        result = {"old_value": {}, "new_value": {}}

        def recursive_diff(old, new):
            """Recursive compare old/new, return (old_value, new_value)"""
            if isinstance(old, dict) and isinstance(new, dict):
                old_res, new_res = {}, {}
                all_keys = set(old.keys()) | set(new.keys())
                for k in all_keys:
                    o_val = old.get(k)
                    n_val = new.get(k)
                    ov, nv = recursive_diff(o_val, n_val)
                    if ov is not None or nv is not None:
                        old_res[k] = ov
                        new_res[k] = nv
                return old_res or None, new_res or None

            elif isinstance(old, list) and isinstance(new, list):
                # primitive list
                if not old or not isinstance(old[0], dict):
                    if old != new:
                        return old, new
                    return None, None
                # list of dict keyed by id
                old_map = (
                    {k: v for k, v in enumerate(old)} if isinstance(old, list) else old
                )
                new_map = (
                    {k: v for k, v in enumerate(new)} if isinstance(new, list) else new
                )

                all_keys = set(old_map.keys()) | set(new_map.keys())
                old_list_res = []
                new_list_res = []
                for k in all_keys:
                    o_val = old_map.get(k)
                    n_val = new_map.get(k)
                    ov, nv = recursive_diff(o_val, n_val)
                    if ov is not None or nv is not None:
                        old_list_res.append({k: ov})
                        new_list_res.append({k: nv})
                if old_list_res or new_list_res:
                    return old_list_res, new_list_res
                return None, None

            else:
                if old != new:
                    return old, new
                return None, None

        ov, nv = recursive_diff(old_data, new_data)
        result["old_value"] = ov or {}
        result["new_value"] = nv or {}
        return result
