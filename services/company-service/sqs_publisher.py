import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

sqs = boto3.client(
    "sqs",
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

JOB_MATCHED_QUEUE_URL = os.getenv("SQS_JOB_MATCHED_URL")


def publish_job_matched(
    job_id: str,
    job_title: str,
    company_name: str,
    location: str,
    job_type: str,
    salary: str,
    description: str,
    matched_phones: list,
) -> bool:
    """
    Publish a job-matched event to SQS.
    The Notification Service consumes this and sends WhatsApp alerts
    to each opted-in matched candidate.
    """
    if not JOB_MATCHED_QUEUE_URL:
        print("[WARN] SQS_JOB_MATCHED_URL not set — skipping publish")
        return False

    message = {
        "job_id":        job_id,
        "job_title":     job_title,
        "company_name":  company_name,
        "location":      location or "",
        "job_type":      job_type or "",
        "salary":        salary or "",
        "description":   description or "",
        "matched_phones": matched_phones,
    }

    try:
        sqs.send_message(
            QueueUrl=JOB_MATCHED_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(f"[INFO] Published job-matched event for job {job_id} → {len(matched_phones)} candidates")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to publish job-matched event: {e}")
        return False
