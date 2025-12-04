import csv
import uuid
import tempfile
import os
import json
import pandas as pd
import requests
from openpyxl import load_workbook
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from modules.file_uploads.models import UploadData, UploadLog, MapLogColumn, JobRequest
from .serializers import UploadFileSerializer
from modules.file_uploads.tasks.process_file import process_file_task
from modules.file_uploads.tasks.classify_tasks import classify_upload_task  # Celery task


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def is_empty_row(row_dict):
    return all(v is None or str(v).strip() == "" for v in row_dict.values())


# -----------------------------
# UPLOAD FILE VIEW
# -----------------------------
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

        return Response({
            "message": "Upload success. Background processing started.",
            "upload_id": upload_id
        })


# -----------------------------
# CLASSIFY UPLOAD DATA VIEW
# -----------------------------
class ClassifyUploadDataView(APIView):
    def post(self, request):
        upload_filename = request.data.get("upload_path")  # filename only
        taxonomy_name = request.data.get("taxonomy_name")
        rules = request.data.get("rules", "")
        job_uuid = request.data.get("job_id")  # external job ID
        account_uuid = request.data.get("account_uuid")  # NEW

        if not upload_filename or not job_uuid:
            return Response({"error": "upload_path and job_id are required"}, status=400)

        # -----------------------------
        # STEP 0 → CREATE JobRequest
        # -----------------------------
        job_request = JobRequest.objects.create(
            params=request.data,
            upload_filename=upload_filename,
            job_id=job_uuid,
            account_id=account_uuid,  # save account ID
            status="pending"
        )

        # -----------------------------
        # STEP 1 → ENQUEUE CELERY TASK
        # -----------------------------
        classify_upload_task.delay(
            job_request_id=job_request.id,
            upload_filename=upload_filename,
            taxonomy_name=taxonomy_name,
            rules=rules,
            job_uuid=job_uuid,
            account_uuid=account_uuid
        )

        return Response({
            "message": "Job request received. AI classification will run in the background.",
            "job_request_id": job_request.job_id,
            "job_status": job_request.status
        }, status=202)


# -----------------------------
# GET JOB DETAILS VIEW
# -----------------------------
class GetJobDetailsView(APIView):

    def get(self, request):
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = JobRequest.objects.get(id=job_id)
        except JobRequest.DoesNotExist:
            return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "job_id": job.id,
            "ai_filepath": job.ai_filepath,
            "statistics": job.statistics,
        }, status=status.HTTP_200_OK)


# -----------------------------
# UPDATE AI JOB VIEW (NEW)
# -----------------------------
class UpdateAiJobView(APIView):
    GRAPHQL_URL = "http://40.81.229.208:8000/api/v1/graphql/data/ai-response/"

    def post(self, request):
        import requests

        job_uuid = request.data.get("uuid")
        ai_file = request.data.get("aiFile")
        stats = request.data.get("stats")

        # Ensure stats is JSON string and then escape it for GraphQL
        if isinstance(stats, dict):
            stats = json.dumps(stats)            # {"a":1,"b":2}
        stats_escaped = json.dumps(stats)[1:-1]  # escapes quotes properly

        x_account = request.headers.get("X-Account")
        api_key = request.headers.get("X-Api-Key")

        # Construct raw GraphQL payload SAFELY
        payload = f"""
                mutation ClassificationJobAiUpdate {{
                  classificationJobAiUpdate(
                    uuid: "{job_uuid}",
                    data: {{
                      aiFile: "{ai_file}",
                      stats: "{stats_escaped}"
                    }}
                  ) {{
                    classificationJob {{
                      createdOn
                      createdBy
                      uuid
                      name
                      aiFile
                      inputFile
                      statuses {{
                        createdOn
                        status
                      }}
                    }}
                  }}
                }}
        """

        print("========== GRAPHQL PAYLOAD SENT ==========")
        print(payload)
        print("==========================================")

        headers = {
            "Content-Type": "application/graphql",
            "X-Api-Key": api_key,
            "X-Account": x_account,
        }

        try:
            response = requests.post(
                self.GRAPHQL_URL,
                data=payload,
                headers=headers,
                timeout=30
            )

            external_result = response.json()

        except Exception as e:
            return Response(
                {"error": "Failed to update external AI job", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "AI job updated successfully",
            "external_api_response": external_result
        })
