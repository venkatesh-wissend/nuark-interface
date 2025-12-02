import uuid
import tempfile
import pandas as pd
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
import os
import json
from .serializers import UploadFileSerializer
from modules.file_uploads.models import UploadData, MapLogColumn, ClassificationTempData, JobRequest
from modules.file_uploads.tasks.process_file import process_file_task
from django.core.files.storage import FileSystemStorage
import requests

from rest_framework import status
from modules.file_uploads.models import UploadData, UploadLog, MapLogColumn, ClassificationTempData


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
        upload_path = request.data.get("upload_path")
        taxonomy_name = request.data.get("taxonomy_name")
        rules = request.data.get("rules", "")
        job_id = request.data.get("job_id")

        if not upload_path:
            return Response({"error": "upload_path is required"}, status=400)
        if not job_id:
            return Response({"error": "job_id is required"}, status=400)

        # -------------------------------------------------------------------------
        # STEP 1 → DOWNLOAD FILE FROM AZURE
        # -------------------------------------------------------------------------
        try:
            file_response = requests.get(upload_path, timeout=60)
            file_response.raise_for_status()
            original_name = upload_path.split("?")[0].split("/")[-1]

            suffix = original_name.split(".")[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
                tmp.write(file_response.content)
                tmp_path = tmp.name

        except Exception as e:
            return Response({"error": f"Failed to download file: {str(e)}"}, status=500)

        # -------------------------------------------------------------------------
        # STEP 2 → PROCESS FILE USING EXISTING FUNCTION
        # -------------------------------------------------------------------------
        try:
            upload_log_id = process_file_task(tmp_path, module="auto_classification")
        except Exception as e:
            return Response({"error": f"Failed to process file: {str(e)}"}, status=500)

        # -------------------------------------------------------------------------
        # STEP 3 → FETCH UPLOADED DATA
        # -------------------------------------------------------------------------
        rows = UploadData.objects.filter(upload_log_id=upload_log_id).order_by("row_id")
        if not rows.exists():
            return Response({"error": "No data found after processing the file"}, status=404)

        # -------------------------------------------------------------------------
        # STEP 4 → LOAD ALIAS MAP
        # -------------------------------------------------------------------------
        alias_map = {}
        for col in MapLogColumn.objects.all():
            for alias in col.alias_names:
                if alias:
                    alias_map[alias.strip().lower()] = col.column_name

        # -------------------------------------------------------------------------
        # STEP 5 → PREPARE AI PAYLOAD
        # -------------------------------------------------------------------------
        products = []
        for row in rows:
            mapped_row = {}
            for key, value in row.data.items():
                standard = alias_map.get(key.strip().lower())
                if standard:
                    mapped_row[standard] = value
            mapped_row["taxonomy_name"] = taxonomy_name
            mapped_row["rules"] = rules
            products.append(mapped_row)

        payload = {"products": products, "max_workers": 5}

        # -------------------------------------------------------------------------
        # STEP 6 → CALL AI API
        # -------------------------------------------------------------------------
        try:
            res = requests.post(
                "https://nuark-13-prod-test-fjexdbfmgngufdex.centralus-01.azurewebsites.net/api/classify",
                json=payload,
                timeout=300
            )
            res.raise_for_status()
            ai_results = res.json()
        except Exception as e:
            return Response({"error": f"AI API failed: {str(e)}"}, status=500)

        ai_output = ai_results.get("results", [])

        # -------------------------------------------------------------------------
        # STEP 7 → UPDATE UploadData & ClassificationTempData
        # -------------------------------------------------------------------------
        for row, ai in zip(rows, ai_output):
            row.ai_data = ai
            row.save(update_fields=["ai_data"])

            # ClassificationTempData.objects.using("nuarkDB").create(
            #     uuid=uuid.uuid4(),
            #     ai_data=ai,
            #     status="ai_completed",
            #     non_editable_data={},
            #     manual_data={},
            #     ai_manual_data={},
            #     created_on=timezone.now(),
            #     updated_on=timezone.now(),
            #     job_id=job_id
            # )

        # -------------------------------------------------------------------------
        # STEP 8 → CONVERT AI OUTPUT TO EXCEL
        # -------------------------------------------------------------------------
        try:
            df_ai = pd.DataFrame(ai_output)
            tmp_excel_path = f"/tmp/ai_output_{job_id}.xlsx"
            df_ai.to_excel(tmp_excel_path, index=False)
        except Exception as e:
            return Response({"error": f"Failed to create Excel: {str(e)}"}, status=500)

        # -------------------------------------------------------------------------
        # STEP 9 → UPLOAD EXCEL & GET PRESIGNED URL
        # -------------------------------------------------------------------------
        try:
            upload_api_url = "http://40.81.229.208:8002/api/v1/upload"
            presigned_url_api = "http://40.81.229.208:8002/api/v1/create_presigned_url"
            headers = {"x-api-key": "xn4vZfSTTRsl7IwMwaIP2A"}

            # Upload
            with open(tmp_excel_path, "rb") as f:
                files = {
                    "file": (f"ai_output_{job_id}.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                }
                upload_resp = requests.post(upload_api_url, headers=headers, files=files)
                upload_resp.raise_for_status()

            # Get signed URL
            params = {"path": f"ai_output_{job_id}.xlsx"}
            presigned_resp = requests.get(presigned_url_api, headers=headers, params=params)
            presigned_resp.raise_for_status()
            signed_url = presigned_resp.json().get("url")
        except Exception as e:
            return Response({"error": f"Failed to upload AI Excel or get URL: {str(e)}"}, status=500)

        # -------------------------------------------------------------------------
        # STEP 10 → UPDATE JobRequest
        # -------------------------------------------------------------------------
        job_request = JobRequest.objects.create(
            params=request.data,
            ai_data=ai_results,
            ai_filepath=signed_url,
        )

        # -------------------------------------------------------------------------
        # STEP 11 → SEND AI RESULTS TO STATISTICS API
        # -------------------------------------------------------------------------
        statistics_payload = {
            "results": ai_output
        }

        try:
            statistics_res = requests.post(
                "https://nuark-13-prod-test-fjexdbfmgngufdex.centralus-01.azurewebsites.net/api/statistics",
                json=statistics_payload,
                timeout=180
            )
            statistics_res.raise_for_status()
            statistics_data = statistics_res.json()
        except Exception as e:
            statistics_data = {"error": f"Statistics API failed: {str(e)}"}

        # -------------------------------------------------------------------------
        # STEP 12 → UPDATE JobRequest WITH STATISTICS RESULT
        # -------------------------------------------------------------------------
        job_request.statistics = statistics_data
        job_request.save(update_fields=["statistics"])

        return Response({
            "message": "Auto-classification completed",
            "ai_results": ai_results,
            "ai_filepath": signed_url,
            'statistics': statistics_data
        }, status=200)

class GetJobDetailsView(APIView):

    def get(self, request):
        job_id = request.data.get("job_id")  # Get job_id from body

        if not job_id:
            return Response({"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = JobRequest.objects.get(id=job_id)
        except JobRequest.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "job_id": job.id,
            # "params": job.params,
            "ai_filepath": job.ai_filepath,
            "statistics": job.statistics,
            # "ai_data": job.ai_data,
        }, status=status.HTTP_200_OK)