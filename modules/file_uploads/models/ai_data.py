from django.db import models

class ClassificationTempData(models.Model):
    id = models.BigAutoField(primary_key=True)

    created_on = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)

    updated_on = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    uuid = models.UUIDField(null=True, blank=True)

    non_editable_data = models.JSONField(null=True, blank=True)
    ai_data = models.JSONField(null=True, blank=True)
    manual_data = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=100, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    reviewed_by = models.CharField(max_length=255, null=True, blank=True)

    job_id = models.BigIntegerField(null=True, blank=True)

    ai_manual_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "classification_temp_data"
        managed = False
