import boto3
import json
import os
import time
import httpx
import redis
from dotenv import load_dotenv

load_dotenv()

sqs = boto3.client(
    "sqs",
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

JOB_MATCHED_QUEUE_URL = os.getenv("SQS_JOB_MATCHED_URL")
WHATSAPP_TOKEN        = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID     = os.getenv("WHATSAPP_PHONE_ID", "")
GRAPH_URL             = "https://graph.facebook.com/v18.0"

_redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)


def _is_opted_in(phone: str) -> bool:
    """Check Redis opt-in cache. Defaults to True if key is missing."""
    val = _redis.get(f"opt_in:{phone}")
    return val != "false"


def _build_message(job_title: str, company_name: str, location: str, job_type: str, salary: str) -> str:
    lines = [
        "🎉 *New Job Match on QuickJobs!*\n",
        f"*{job_title}*",
        f"🏢 {company_name}",
    ]
    if location:
        lines.append(f"📍 {location}")
    if job_type:
        lines.append(f"💼 {job_type}")
    if salary:
        lines.append(f"💰 {salary}")
    lines.append("\nThis listing matches your skills and experience.")
    lines.append("\n_Send *STOP* to unsubscribe from alerts._")
    return "\n".join(lines)


def _send_whatsapp(to: str, message: str) -> bool:
    """Send a WhatsApp text message via Meta Graph API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print(f"[WARN] WhatsApp credentials not set — skipping notification to {to}")
        return False
    try:
        resp = httpx.post(
            f"{GRAPH_URL}/{WHATSAPP_PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            },
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"[INFO] Notified {to}")
            return True
        print(f"[WARN] WhatsApp API returned {resp.status_code} for {to}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp to {to}: {e}")
    return False


def process_job_matched(body: dict) -> None:
    """
    Handle a job-matched event from SQS.
    Sends a WhatsApp notification to every opted-in matched candidate.
    """
    job_id        = body.get("job_id", "")
    job_title     = body.get("job_title", "Job Opportunity")
    company_name  = body.get("company_name", "")
    location      = body.get("location", "")
    job_type      = body.get("job_type", "")
    salary        = body.get("salary", "")
    phones        = body.get("matched_phones", [])

    if not phones:
        print(f"[INFO] No matched phones for job {job_id}")
        return

    message = _build_message(job_title, company_name, location, job_type, salary)
    sent = 0

    for phone in phones:
        if _is_opted_in(phone):
            if _send_whatsapp(phone, message):
                sent += 1
        else:
            print(f"[INFO] Skipping {phone} — opted out")

    print(f"[INFO] Job {job_id}: notified {sent}/{len(phones)} candidates")


def poll_job_matched_queue() -> None:
    """
    Continuously poll SQS for job-matched events.
    Runs as a background daemon thread.
    """
    print("[INFO] Notification Service — waiting for job-matched events...")

    while True:
        if not JOB_MATCHED_QUEUE_URL:
            print("[WARN] SQS_JOB_MATCHED_URL not set — sleeping")
            time.sleep(10)
            continue

        try:
            response = sqs.receive_message(
                QueueUrl=JOB_MATCHED_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )
            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg["Body"])
                    process_job_matched(body)
                    sqs.delete_message(
                        QueueUrl=JOB_MATCHED_QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"],
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to process message: {e}")
        except Exception as e:
            print(f"[ERROR] SQS poll error: {e}")
            time.sleep(5)

        time.sleep(1)


if __name__ == "__main__":
    poll_job_matched_queue()
