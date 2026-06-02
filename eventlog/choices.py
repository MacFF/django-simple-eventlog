from django.db.models import TextChoices

class EventLogAction(TextChoices):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"
