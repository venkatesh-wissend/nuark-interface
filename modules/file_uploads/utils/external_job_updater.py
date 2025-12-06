import json
import requests
from urllib.parse import urlparse, unquote

def update_external_ai_job(job_uuid, ai_file, stats, x_account, api_key):
    # Ensure header values are strings
    x_account = str(x_account)
    job_uuid = str(job_uuid)

    parsed_url = urlparse(ai_file)
    ai_file = unquote(parsed_url.path.split("/")[-1])


    if isinstance(stats, dict):
        stats = json.dumps(stats)

    stats_escaped = json.dumps(stats)[1:-1]

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

    response = requests.post(
        "http://40.81.229.208:8000/api/v1/graphql/data/ai-response/",
        data=payload,
        headers=headers,
        timeout=30,
    )
    return response.json()
