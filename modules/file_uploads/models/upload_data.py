from django.db import models
from django.db.models import JSONField
import uuid

class UploadData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    row_id = models.IntegerField()
    data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    module = models.CharField(max_length=100, null=True, blank=True)
    ai_data = models.JSONField(null=True, blank=True)

    upload_log = models.ForeignKey(
        "UploadLog",  # use string reference instead of importing
        on_delete=models.CASCADE,
        related_name="rows",
        null=True,
        blank=True
    )

    class Meta:
        db_table = "upload_data"
