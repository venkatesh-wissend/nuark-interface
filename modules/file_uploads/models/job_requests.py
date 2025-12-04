from django.db import models
from django.utils import timezone
import uuid

class JobRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),        # Job created, waiting for processing
        ("processing", "Processing"),  # Celery task is running
        ("completed", "Completed"),    # AI classification finished successfully
        ("failed", "Failed"),          # Task failed
    ]

    id = models.AutoField(primary_key=True)
    params = models.JSONField(null=True, blank=True)
    ai_data = models.JSONField(null=True, blank=True)
    ai_filepath = models.CharField(max_length=500, null=True, blank=True)
    statistics = models.JSONField(null=True, blank=True)
    job_id = models.CharField(max_length=255, default=uuid.uuid4, null=True, blank=True, editable=False)
    upload_filename = models.CharField(max_length=255, null=True, blank=True)
    account_id = models.UUIDField(null=True, blank=True)  # NEW: store account UUID
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField( auto_now_add=True, null=True )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"JobRequest #{self.id} ({self.job_id}) - {self.status}"
