from django.db import models
import uuid

class JobRequest(models.Model):
    id = models.AutoField(primary_key=True)
    params = models.JSONField(null=True, blank=True)           # Stores request params
    ai_data = models.JSONField(null=True, blank=True)          # AI output data
    ai_filepath = models.CharField(max_length=500, null=True, blank=True)  # Path to AI processed file
    statistics = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "job_requests"

    def __str__(self):
        return f"JobRequest #{self.id}"
