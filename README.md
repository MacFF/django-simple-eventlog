# django-simple-eventlog

A reusable Django application for tracking and logging events and model changes. This library provides a structured way to maintain audit trails for user actions and system events.

## Installation

You can install the package directly into your project via PyPI using `uv` (or `pip`):

```bash
uv add django-simple-eventlog
```
```bash
pip install django-simple-eventlog
```

Add `eventlog` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django_simple_eventlog',
    # ...
]
```

Run migrations to create the required database tables:

```bash
python manage.py makemigrations django_simple_eventlog
python manage.py migrate
```

## Core Concepts

The library provides two primary components:
- `EventLog`: The main model that stores the log entry, who performed the action, which object was affected, and a JSON payload of changes.
- `EventLogService`: A helper class to automatically generate diffs and create the log entries cleanly.

## Usage

### 1. Logging an Event

Use `EventLogService.log` to record an event. Here is a practical example of logging when an item is updated or deleted within a ViewSet:

```python
from rest_framework import viewsets
from rest_framework.response import Response
from django.db import transaction
from django_simple_eventlog.services import EventLogService
from django_simple_eventlog.choices import EventLogAction

class ExampleViewSet(viewsets.ModelViewSet):
    # ...

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 1. Store the old data
        old_data = self.get_serializer(instance).data
        
        # 2. Perform the update
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # 3. Store the new data
        new_data = serializer.data

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        # 4. Generate the diff schema between old and new data
        changes = EventLogService.create_diff_schema(old_data, new_data)
        
        # 5. Log the update event
        EventLogService.log(
            template_message="Item {item__name} was updated by {user__full_name}.",
            values_json={
                "item__name": instance, 
                "user__full_name": self.request.user
            }, 
            object=instance,
            actor=self.request.user,
            tool="example_feature",
            action=EventLogAction.UPDATE,
            changes=changes,
        )
        return Response(serializer.data)

    @transaction.atomic
    def perform_destroy(self, instance):
        # Delete the object
        super().perform_destroy(instance)
        
        # Log the delete event
        EventLogService.log(
            template_message="Item {item__name} was deleted by {user__full_name}.",
            values_json={
                "item__name": instance,
                "user__full_name": self.request.user,
            },
            object=instance,
            actor=self.request.user,
            tool="example_feature",
            action=EventLogAction.DELETE,
        )
```

You can also log events directly from your Serializers, such as when creating a new object:

```python
from rest_framework import serializers
from django.db import transaction
from django_simple_eventlog.services import EventLogService
from django_simple_eventlog.choices import EventLogAction

class ExampleSerializer(serializers.ModelSerializer):
    # ... your fields ...

    @transaction.atomic
    def create(self, validated_data):
        # 1. Create the object
        obj = super().create(validated_data)
        
        # 2. Get the user from the serializer context
        user = self.context['request'].user
        
        # 3. Log the create event
        EventLogService.log(
            template_message="Created a new request", 
            object=obj,
            actor=user,
            tool="example_request",
            action=EventLogAction.CREATE,
        )
        return obj
```

#### Parameter Breakdown

* **`template_message` & `values_json` (Format Strings):**  
  These two parameters work together to create dynamic text. In the example above, `{inspection_team__name}` is a format string. The prefix `inspection_team` is just for readability, but the crucial part is `__name`. It tells the service to look at the `values_json` dictionary, find the key `"inspection_team__name"`, take the object provided (`instance`), and extract its `name` attribute. The same logic applies to `{user__full_name}`: it looks for `"user__full_name"` in `values_json`, takes `self.request.user`, and extracts its `full_name` attribute.
  
* **`actor`**: The user who made the request or caused this event (usually `request.user`).
* **`tool`**: A string used to categorize logs by app or feature (e.g., `"certificate"`, `"user"`, `"inspection_team"`). This is very helpful when you want to filter logs by feature via the API.
* **`action`**: A string indicating what method or action was performed (`create`, `update`, `delete`). We provide `EventLogAction` choices, but you can pass custom strings.
* **`object`**: The main target object of this event log (e.g., the specific inspection team or certificate being deleted/updated).
* **`changes`**: Used mainly for updates. You can generate a diff between the old and new states using `EventLogService.create_diff_schema(old_data, new_data)` to record exactly what changed.

### 2. Generating Diffs

If you have two dictionaries representing the before and after states (e.g., from a DRF serializer), you can generate a schema of what changed:

```python
old_data = {"name": "John", "status": "active"}
new_data = {"name": "John", "status": "inactive"}

diff = EventLogService.create_diff_schema(old_data, new_data, exclude_keys=["updated_at"])
# Returns: {"old_value": {"status": "active"}, "new_value": {"status": "inactive"}}
```

### 3. Provided Log ViewSet and Mixin

We provide ready-to-use components to easily expose your event logs via a REST API.

#### `EventLogViewSet`

To expose the REST API endpoints for viewing all logs, you can wire up the `EventLogViewSet` into your project's URL configuration. 

This ViewSet is particularly useful when you want to filter logs by `tool` to see all events that occurred within a specific feature across your application (e.g., `GET /api/eventlogs/?tool=example_feature`).

In your project's `urls.py`, import the viewset and register it with a Django REST Framework router:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django_simple_eventlog.views import EventLogViewSet

# Create a router and register our viewset
router = DefaultRouter()
router.register(r'eventlogs', EventLogViewSet, basename='eventlog')

urlpatterns = [
    # ... your other url patterns ...
    path('api/', include(router.urls)),
]
```

*(Note: If your project already uses a router, simply import `EventLogViewSet` and register it along with your other endpoints.)*

#### `EventLogMixin`

We also provide a handy `EventLogMixin` that you can add to any of your existing DRF ViewSets. Once added, it automatically creates a route at `GET /your-endpoint/<id>/log/` so you can view all events related to that specific object!

```python
from rest_framework import viewsets
from django_simple_eventlog.mixins import EventLogMixin

class CertificateViewSet(EventLogMixin, viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    
    # That's it! You can now call GET /certificates/1/log/
```

**Example Response:**

```json
{
    "count": 2,
    "results": [
        {
            "id": 2,
            "actor": "John Doe",
            "message": "Item Certificate A was updated by John Doe.",
            "timestamp": "2023-11-12T15:26:12.275092Z",
            "object_id": 1,
            "tool": "example_feature",
            "action": "update",
            "changes": {
                "new_value": {
                    "status": "inactive"
                },
                "old_value": {
                    "status": "active"
                }
            },
            "object_type": 15
        },
        {
            "id": 1,
            "actor": "John Doe",
            "message": "Created a new request",
            "timestamp": "2023-11-12T15:25:23.776353Z",
            "object_id": 1,
            "tool": "example_request",
            "action": "create",
            "changes": null,
            "object_type": 15
        }
    ]
}
```
