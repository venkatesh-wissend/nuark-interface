# modules/file_uploads/models/ai_result.py

from django.db import models

class AIData(models.Model):
    upload_log_id = models.UUIDField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_data"
        app_label = "modules_file_uploads"

