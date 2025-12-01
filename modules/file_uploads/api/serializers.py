from rest_framework import serializers
from modules.file_uploads.models.column_map import MapLogColumn

class UploadFileSerializer(serializers.Serializer):
    file = serializers.FileField()
    module = serializers.CharField(required=False, allow_blank=True)

class MapLogColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapLogColumn
        fields = ['id', 'column_name', 'alias_names']