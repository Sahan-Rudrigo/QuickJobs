import boto3
import json
import os
import time
import httpx
from dotenv import load_dotenv
from embedder import upsert_user_vectors, should_re_embed
from cv_parser import parse_cv_sections

load_dotenv()


sqs = boto3.client(
    'sqs',
    region_name='ap-south-1',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

CV_QUEUE_URL = os.getenv("SQS_CV_UPLOADED_URL")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")


def get_user_profile(phone: str) -> dict:
    """
    Fetch candidate profile from User Service.
    Returns None if user not found.
    """
    try:
        response = httpx.get(
            f"{USER_SERVICE_URL}/users/{phone}",
            timeout=10.0
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[WARN] User {phone} not found in User Service")
            return None
    except Exception as e:
        print(f"[ERROR] Could not reach User Service: {e}")
        return None


def update_user_cv_fields(phone: str, s3_key: str, version: int):
    """
    Update cv_s3_key and cv_version in User Service
    after successful embedding.
    """
    try:
        response = httpx.patch(
            f"{USER_SERVICE_URL}/users/{phone}",
            json={
                "cv_s3_key": s3_key,
                "cv_version": version
            },
            timeout=10.0
        )
        if response.status_code == 200:
            print(f"[INFO] Updated CV fields for {phone}")
        else:
            print(f"[WARN] Failed to update CV fields for {phone}: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Could not update User Service: {e}")


def process_cv_uploaded(body: dict):
    """
    Full pipeline when a CV upload event arrives from SQS:
    1. Get user profile from User Service
    2. Parse CV text into 3 sections
    3. Check if re-embedding is needed
    4. Store vectors in Pinecone
    5. Update User Service with CV metadata
    """
    phone = body.get("phone")
    extracted_text = body.get("extracted_text", "")
    s3_key = body.get("s3_key", "")
    version = body.get("version", 1)

    if not phone:
        print(f"[ERROR] Missing phone in SQS message: {body}")
        return

    if len(extracted_text) < 50:
        print(f"[WARN] CV text too short for {phone} — skipping embedding")
        return

    print(f"[INFO] Processing CV for {phone} (version {version})")

    # Step 1 — Get user profile for fallback data
    user = get_user_profile(phone)
    fallback_skills = user.get("skills", []) if user else []
    fallback_experience = user.get("experience_level", "") if user else ""

    # Step 2 — Parse CV text into 3 sections
    sections = parse_cv_sections(
        raw_text=extracted_text,
        fallback_skills=fallback_skills,
        fallback_experience=fallback_experience
    )

    print(f"[INFO] Parsed sections for {phone}:")
    print(f"  Skills: {sections['skills'][:60]}...")
    print(f"  Experience: {sections['experience'][:60]}...")
    print(f"  Summary length: {len(sections['summary'])} chars")

    # Step 3 — Check if re-embedding is needed
    if not should_re_embed(phone, sections):
        print(f"[INFO] Skipping re-embed for {phone} — change too small")
        return

    # Step 4 — Store vectors in Pinecone
    upsert_user_vectors(phone, sections, version)

    # Step 5 — Update User Service with CV metadata
    update_user_cv_fields(phone, s3_key, version)

    print(f"[INFO] Successfully processed CV for {phone}")


def poll_cv_queue():
    """
    Continuously poll SQS for cv.uploaded events.
    Runs as a background thread — never stops.
    """
    print("[INFO] CV queue consumer started — waiting for events...")

    while True:
        # Skip if queue URL not configured yet
        if not CV_QUEUE_URL:
            print("[WARN] SQS_CV_UPLOADED_URL not set — retrying in 5s")
            time.sleep(5)
            continue

        try:
            response = sqs.receive_message(
                QueueUrl=CV_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20  # long polling
            )

            messages = response.get("Messages", [])

            for msg in messages:
                try:
                    body = json.loads(msg["Body"])
                    process_cv_uploaded(body)

                    # Delete ONLY after successful processing
                    sqs.delete_message(
                        QueueUrl=CV_QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"]
                    )
                    print(f"[INFO] Message deleted from queue")

                except Exception as e:
                    print(f"[ERROR] Failed to process message: {e}")
                    # Do NOT delete — let it retry or go to DLQ
                    time.sleep(5)

        except Exception as e:
            print(f"[ERROR] SQS polling error: {e}")
            time.sleep(5)

        time.sleep(1)


if __name__ == "__main__":
    poll_cv_queue()