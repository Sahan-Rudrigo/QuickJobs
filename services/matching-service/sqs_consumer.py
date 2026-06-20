import boto3
import json
import os
import time
from dotenv import load_dotenv
from embedder import embed_cv, index

load_dotenv()

sqs = boto3.client(
    'sqs',
    region_name='ap-south-1',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

CV_QUEUE_URL = os.getenv("SQS_CV_UPLOADED_URL")


def process_cv_uploaded(body: dict):
    """
    Called when a CV upload event arrives from SQS.
    Embeds the candidate profile and stores vectors in Pinecone.
    """
    phone = body.get("phone")
    skills = body.get("skills", [])
    experience = body.get("experience", "")
    full_text = body.get("full_text", "")

    if not phone:
        print(f"[ERROR] Missing phone in message: {body}")
        return

    print(f"[INFO] Processing CV for {phone}")

    # Generate 3 vectors for this candidate
    vectors = embed_cv(phone, skills, experience, full_text)

    # Store in Pinecone
    index.upsert(vectors=vectors)

    print(f"[INFO] Embedded and stored vectors for {phone}")


def poll_cv_queue():
    """
    Continuously poll SQS for new CV upload events.
    This runs as a background process.
    """
    print("[INFO] Starting SQS consumer — waiting for CV events...")

    while True:
        # Skip if queue URL not configured yet
        if not CV_QUEUE_URL:
            print("[WARN] SQS_CV_UPLOADED_URL not set — skipping poll")
            time.sleep(5)
            continue

        response = sqs.receive_message(
            QueueUrl=CV_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20  # long polling — efficient, not spammy
        )

        messages = response.get("Messages", [])

        for msg in messages:
            try:
                body = json.loads(msg["Body"])
                process_cv_uploaded(body)

                # Delete message after successful processing
                sqs.delete_message(
                    QueueUrl=CV_QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )
            except Exception as e:
                print(f"[ERROR] Failed to process message: {e}")
                # Don't delete — let it retry or go to DLQ

        time.sleep(1)


if __name__ == "__main__":
    poll_cv_queue()