import boto3
import os
from dotenv import load_dotenv

load_dotenv()

MAX_CV_VERSIONS = 3

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION", "ap-south-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

BUCKET = os.getenv("S3_BUCKET_NAME", "quickjobs-cvs")


def build_s3_key(phone: str, version: int, filename: str) -> str:
    return f"cvs/{phone}/v{version}/{filename}"


def upload_cv(phone: str, version: int, filename: str, file_bytes: bytes, mime_type: str) -> str:
    """Upload CV bytes to S3 and return the S3 key."""
    key = build_s3_key(phone, version, filename)
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=mime_type,
    )
    return key


def delete_cv(s3_key: str) -> None:
    """Delete a CV file from S3."""
    try:
        s3.delete_object(Bucket=BUCKET, Key=s3_key)
    except Exception as e:
        print(f"[WARN] Failed to delete S3 object {s3_key}: {e}")


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a temporary download URL for a CV."""
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )
