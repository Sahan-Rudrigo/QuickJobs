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

CV_QUEUE_URL = os.getenv("SQS_CV_UPLOADED_URL")


def publish_cv_uploaded(
    phone: str,
    s3_key: str,
    cv_version: int,
    skills: list,
    experience: str,
    full_text: str,
) -> bool:
    """
    Publish a cv.uploaded event to SQS.
    The Matching Service consumer picks this up and embeds the CV in Pinecone.
    """
    if not CV_QUEUE_URL:
        print("[WARN] SQS_CV_UPLOADED_URL not set — skipping publish")
        return False

    message = {
        "phone":      phone,
        "s3_key":     s3_key,
        "cv_version": cv_version,
        "skills":     skills,
        "experience": experience,
        "full_text":  full_text[:4000],  # cap to avoid SQS 256KB limit
    }

    try:
        sqs.send_message(
            QueueUrl=CV_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(f"[INFO] Published cv.uploaded for {phone} v{cv_version}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to publish SQS message: {e}")
        return False
