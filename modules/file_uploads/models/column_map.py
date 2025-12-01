from django.db import models
from django.contrib.postgres.fields import ArrayField   # Works only with PostgreSQL

class MapLogColumn(models.Model):
    column_name = models.CharField(max_length=255)
    alias_names = ArrayField(
        models.CharField(max_length=255),
        default=list,     # alias names as list ["Product Title", "Title of product"]
        blank=True
    )

    class Meta:
        db_table = "column_map"

    def __str__(self):
        return self.column_name
