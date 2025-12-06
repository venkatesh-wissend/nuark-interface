import tempfile
import pandas as pd
import requests
from celery import shared_task
from modules.file_uploads.models import UploadData, MapLogColumn, JobRequest
from modules.file_uploads.tasks.process_file import process_file_task
from modules.file_uploads.utils.external_job_updater import update_external_ai_job
import math

BATCH_SIZE = 100  # Number of products per AI API call

@shared_task(bind=True, max_retries=3)
def classify_upload_task(self, job_request_id, upload_filename, taxonomy_name, rules, job_uuid, account_uuid=None):
    """
    Celery task to classify uploaded data using AI, generate Excel, upload to Azure,
    and store results/statistics in JobRequest.
    """
    print("=========== TASK STARTED ===========")

    try:
        # -----------------------------
        # GET JOB REQUEST
        # -----------------------------
        job_request = JobRequest.objects.get(id=job_request_id)
        job_request.status = "processing"
        job_request.save(update_fields=["status"])
        print(f"JobRequest #{job_request_id} status set to PROCESSING")

        # -----------------------------
        # GET PRESIGNED AZURE URL
        # -----------------------------
        presigned_url_api = "http://40.81.229.208:8002/api/v1/create_presigned_url"
        headers = {"x-api-key": "xn4vZfSTTRsl7IwMwaIP2A"}

        presigned_resp = requests.get(
            presigned_url_api,
            headers=headers,
            params={"path": upload_filename},
            timeout=30
        )
        presigned_resp.raise_for_status()
        upload_path = presigned_resp.json().get("url")
        if not upload_path:
            raise ValueError(f"Failed to generate presigned URL for {upload_filename}")

        print(f"Generated presigned URL: {upload_path}")

        # -----------------------------
        # DOWNLOAD FILE
        # -----------------------------
        file_response = requests.get(upload_path, timeout=60)
        file_response.raise_for_status()

        suffix = upload_filename.split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            tmp.write(file_response.content)
            tmp_path = tmp.name

        print(f"Temporary file saved at: {tmp_path}")

        # -----------------------------
        # PROCESS FILE
        # -----------------------------
        upload_log_id = process_file_task( file_path=tmp_path, module="auto_classification", original_filename=upload_filename )
        rows = UploadData.objects.filter(upload_log_id=upload_log_id).order_by("row_id")

        if not rows.exists():
            print("No rows found. Ending task.")
            job_request.status = "failed"
            job_request.save(update_fields=["status"])
            return

        # -----------------------------
        # LOAD ALIAS MAP
        # -----------------------------
        alias_map = {}
        for col in MapLogColumn.objects.all():
            for alias in col.alias_names:
                if alias:
                    alias_map[alias.strip().lower()] = col.column_name

        # -----------------------------
        # PREPARE DATA FOR AI
        # -----------------------------
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

        # -----------------------------
        # CALL AI API IN BATCHES
        # -----------------------------
        all_ai_results = []
        total_batches = math.ceil(len(products) / BATCH_SIZE)

        for i in range(total_batches):
            batch_products = products[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
            payload = {"products": batch_products, "max_workers": 2}

            try:
                res = requests.post(
                    "https://nuark-13-prod-test-fjexdbfmgngufdex.centralus-01.azurewebsites.net/api/classify",
                    json=payload,
                    timeout=30000
                )
                res.raise_for_status()
                batch_results = res.json().get("results", [])
                all_ai_results.extend(batch_results)
            except Exception as e:
                print(f"Error in batch {i+1}, retrying... {e}")
                raise self.retry(exc=e, countdown=60)

        # -----------------------------
        # UPDATE UploadData
        # -----------------------------
        for row, ai in zip(rows, all_ai_results):
            row.ai_data = ai
            row.save(update_fields=["ai_data"])

        # -----------------------------
        # MERGE ORIGINAL INPUT + AI OUTPUT
        # -----------------------------
        flattened_results = []

        for row, ai in zip(rows, all_ai_results):
            merged = {}

            # 1️⃣ Add original user-uploaded columns
            for key, value in row.data.items():
                merged[key] = value

            # 2️⃣ Add AI fields
            classification = ai.get("classification", {})

            merged["LLM_approach"] = classification.get("LLM_approach", "")
            merged["LLM_end_node"] = classification.get("LLM_end_node", "")
            merged["LLM_picked_taxonomy"] = classification.get("LLM_picked_taxonomy", "")

            flattened_results.append(merged)
        # -----------------------------
        # CREATE EXCEL
        # -----------------------------
        df_ai = pd.DataFrame(flattened_results)
        tmp_excel_path = f"/tmp/ai_output_{job_request_id}.xlsx"
        df_ai.to_excel(tmp_excel_path, index=False)

        # -----------------------------
        # UPLOAD EXCEL
        # -----------------------------
        upload_api_url = "http://40.81.229.208:8002/api/v1/upload"
        with open(tmp_excel_path, "rb") as f:
            files = {
                "file": (f"ai_output_{job_request_id}.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            }
            upload_resp = requests.post(upload_api_url, headers=headers, files=files)
            upload_resp.raise_for_status()

        presigned_resp = requests.get(presigned_url_api, headers=headers, params={"path": f"ai_output_{job_request_id}.xlsx"})
        presigned_resp.raise_for_status()
        signed_url = presigned_resp.json().get("url")

        # -----------------------------
        # UPDATE JobRequest
        # -----------------------------
        job_request.ai_data = all_ai_results
        job_request.ai_filepath = signed_url

        # -----------------------------
        # CALL STATISTICS API
        # -----------------------------
        statistics_payload = {"results": all_ai_results, "account_id": str(account_uuid)}
        try:
            statistics_res = requests.post(
                "https://nuark-13-prod-test-fjexdbfmgngufdex.centralus-01.azurewebsites.net/api/statistics",
                json=statistics_payload,
                timeout=180
            )
            statistics_res.raise_for_status()
            job_request.statistics = statistics_res.json()
        except Exception as e:
            job_request.statistics = {"error": str(e)}

        # -----------------------------
        # MARK JOB AS COMPLETED
        # -----------------------------
        job_request.status = "completed"
        job_request.save(update_fields=["ai_data", "ai_filepath", "statistics", "status"])

        print(f"=========== TASK COMPLETED SUCCESSFULLY for JobRequest #{job_request_id} ===========")

        try:
            graphql_result = update_external_ai_job(
                job_uuid=job_request.job_id,
                ai_file=job_request.ai_filepath,
                stats=job_request.statistics,
                x_account=str(job_request.account_id),
                api_key='VhMdRrZa.fjZ5LWOyk6HghPyvNnfQ1BlvtsLPtRpz'
            )

            print("GraphQL update successful:", graphql_result)

        except Exception as e:
            print("GraphQL update FAILED:", e)


    except Exception as exc:
        print(f"TASK FAILED – RETRYING: {exc}")
        job_request.status = "failed"
        job_request.save(update_fields=["status"])
        raise self.retry(exc=exc, countdown=60)
