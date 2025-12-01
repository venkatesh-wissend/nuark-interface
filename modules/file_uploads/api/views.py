from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
import json
from .serializers import UploadFileSerializer
from modules.file_uploads.tasks.process_file import process_file_task
from django.core.files.storage import FileSystemStorage
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from modules.file_uploads.models import UploadData, UploadLog, MapLogColumn, AIData

class UploadFileView(APIView):

    def post(self, request):
        serializer = UploadFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["file"]
        module = serializer.validated_data.get("module")
        filename = file.name

        allowed = (".xlsx", ".csv")

        if not filename.lower().endswith(allowed):
            return Response({"error": "Only .xlsx or .csv allowed"}, status=400)

        upload_path = os.path.join(settings.BASE_DIR, "uploads")
        os.makedirs(upload_path, exist_ok=True)

        fs = FileSystemStorage(location=upload_path)
        saved_name = fs.save(filename, file)
        file_path = os.path.join(upload_path, saved_name)

        upload_id = process_file_task(file_path, module)

        return Response({"message": "Upload success. Background processing started.", "upload_id": upload_id})


class ClassifyUploadDataView(APIView):

    def post(self, request):
        upload_log_id = request.data.get("upload_log_id")
        taxonomy_name = request.data.get("taxonomy_name")
        rules = request.data.get("rules")
        max_workers = request.data.get("max_workers", 2)

        if not upload_log_id:
            return Response({"error": "upload_log_id is required"}, status=400)

        # Fetch uploaded data rows
        rows = UploadData.objects.filter(upload_log_id=upload_log_id)
        if not rows.exists():
            return Response({"error": "No upload data found for this log"}, status=404)

        # --------------------------------------------------------------------------------
        # BUILD ALIAS MAP FROM MAP LOG TABLE
        # --------------------------------------------------------------------------------

        map_columns = MapLogColumn.objects.all()

        # alias → standard name mapping
        alias_map = {}

        for col in map_columns:
            # Make sure alias_names is list
            if not col.alias_names:
                continue

            for alias in col.alias_names:
                if alias:
                    alias_map[alias.strip().lower()] = col.column_name

        # Debug: print built alias map
        print("\n=== Alias Map Loaded ===")
        for k, v in alias_map.items():
            print(k, "=>", v)
        print("========================\n")

        # --------------------------------------------------------------------------------
        # BUILD PRODUCT PAYLOAD FOR EXTERNAL API
        # --------------------------------------------------------------------------------

        products = []

        for row in rows:
            mapped_row = {}

            for key, value in row.data.items():

                normalized = key.strip().lower()

                standard = alias_map.get(normalized)

                # Debug unmapped keys to fix later in alias table
                if not standard:
                    print("UNMAPPED COLUMN:", key)
                    continue

                mapped_row[standard] = value

            # Ensure required default fields
            # mapped_row["taxonomy_name"] = mapped_row.get("taxonomy_name",
            #                                              "hybrid_ah_taxonomy_production")
            # mapped_row["rules"] = mapped_row.get("rules", "")

            mapped_row["taxonomy_name"] = taxonomy_name
            mapped_row["rules"] =rules

            products.append(mapped_row)

        payload = {
            "products": products,
            "max_workers": max_workers
        }

        print("\n=== Payload Sent to AI ===")
        print(json.dumps(payload, indent=4))
        print("==========================\n")

        # --------------------------------------------------------------------------------
        # CALL EXTERNAL CLASSIFY API
        # --------------------------------------------------------------------------------

        try:
            response = requests.post(
                "https://nuark-13-prod-test-fjexdbfmgngufdex.centralus-01.azurewebsites.net/api/classify",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            ai_results = response.json()

        except requests.RequestException as e:
            return Response({"error": f"External API call failed: {str(e)}"}, status=500)

        # --------------------------------------------------------------------------------
        # SAVE AI RESULTS BACK TO DATABASE
        # --------------------------------------------------------------------------------
        rows = rows.order_by("id")

        # Correct key from API response
        ai_output = ai_results.get("results", [])

        for row, result in zip(rows, ai_output):
            row.ai_data = result
            row.save(update_fields=["ai_data"])

            AIData.objects.using("wissendDB").create(
                upload_log_id=row.upload_log_id,
                data=result
            )

        return Response({
            "message": "Classification complete",
            "ai_results": ai_results
        }, status=200)