import boto3
import json
import os
import time
import httpx
from dotenv import load_dotenv
from embedder import embed_cv, index

load_dotenv()

sqs = boto3.client(
    'sqs',
    region_name='ap-south-1',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

CV_QUEUE_URL         = os.getenv("SQS_CV_UPLOADED_URL")
COMPANY_SERVICE_URL  = os.getenv("COMPANY_SERVICE_URL", "http://localhost:8003")


def _notify_company_service(phone: str, job_ids: list) -> None:
    """
    For each matched job, tell Company Service to notify this candidate.
    Company Service records them as NOTIFIED and sends a WhatsApp offer —
    they only become visible to the employer once they reply APPLY.
    """
    for job_id in job_ids:
        try:
            httpx.post(
                f"{COMPANY_SERVICE_URL}/jobs/{job_id}/notify-match",
                json={"phones": [phone]},
                timeout=5,
            )
        except Exception as e:
            print(f"[WARN] Could not notify company-service for job {job_id}: {e}")


def process_cv_uploaded(body: dict):
    """
    Called when a CV upload event arrives from SQS.
    1. Embed the candidate profile into Pinecone.
    2. Run reverse matching to find active jobs that match this candidate.
    3. Notify Company Service so employer dashboards update immediately.
    """
    phone      = body.get("phone")
    skills     = body.get("skills", [])
    experience = body.get("experience", "")
    full_text  = body.get("full_text", "")

    if not phone:
        print(f"[ERROR] Missing phone in message: {body}")
        return

    print(f"[INFO] Processing CV for {phone}")

    # Step 1: embed and store candidate vectors
    vectors = embed_cv(phone, skills, experience, full_text)
    index.upsert(vectors=vectors)
    print(f"[INFO] Embedded and stored vectors for {phone}")

    # Step 2: reverse match — find jobs that match this candidate
    try:
        from matcher import find_matching_jobs
        matched_job_ids = find_matching_jobs(
            phone=phone,
            skills=skills,
            experience=experience,
            full_text=full_text,
        )
        if matched_job_ids:
            print(f"[INFO] Reverse match: {phone} matched {len(matched_job_ids)} job(s)")
            _notify_company_service(phone, matched_job_ids)
        else:
            print(f"[INFO] No reverse job matches for {phone}")
    except Exception as e:
        print(f"[WARN] Reverse matching failed for {phone}: {e}")


def poll_cv_queue():
    """
    Continuously poll SQS for new CV upload events.
    Runs as a background daemon thread.
    """
    print("[INFO] Starting SQS consumer — waiting for CV events...")

    while True:
        if not CV_QUEUE_URL:
            print("[WARN] SQS_CV_UPLOADED_URL not set — skipping poll")
            time.sleep(5)
            continue

        try:
            response = sqs.receive_message(
                QueueUrl=CV_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )

            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg["Body"])
                    process_cv_uploaded(body)
                    sqs.delete_message(
                        QueueUrl=CV_QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"]
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to process message: {e}")
        except Exception as e:
            print(f"[ERROR] SQS poll error: {e}")
            time.sleep(5)

        time.sleep(1)


if __name__ == "__main__":
    poll_cv_queue()
