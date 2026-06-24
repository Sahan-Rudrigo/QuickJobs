import httpx
import os


GRAPH_URL = "https://graph.facebook.com/v18.0"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"}


async def send_text(to: str, message: str) -> None:
    """Send a WhatsApp text message."""
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GRAPH_URL}/{phone_id}/messages",
            headers=_auth_headers(),
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            },
        )


async def get_media_url(media_id: str) -> tuple[str, str]:
    """
    Get download URL and MIME type for a media object from Meta.
    Returns (url, mime_type).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_URL}/{media_id}",
            headers=_auth_headers(),
        )
        data = resp.json()
        return data["url"], data.get("mime_type", "application/pdf")


async def download_media(media_id: str) -> tuple[bytes, str, str]:
    """
    Download a media file from Meta.
    Returns (file_bytes, mime_type, filename).
    """
    url, mime_type = await get_media_url(media_id)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_auth_headers())

    ext_map = {
        "application/pdf": "cv.pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "cv.docx",
        "application/msword": "cv.doc",
    }
    filename = ext_map.get(mime_type, "cv.pdf")
    return resp.content, mime_type, filename


async def forward_cv_to_file_service(
    phone: str,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    skills: list,
    experience: str,
) -> dict:
    """
    Send CV file to the File Service for extraction, S3 upload, and SQS publish.
    Returns the File Service response JSON.
    """
    import json
    file_service_url = os.getenv("FILE_SERVICE_URL", "http://localhost:8002")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{file_service_url}/cv/upload/{phone}",
            files={"file": (filename, file_bytes, mime_type)},
            data={
                "skills":     json.dumps(skills),
                "experience": experience,
            },
        )

    if resp.status_code != 200:
        print(f"[ERROR] File Service returned {resp.status_code}: {resp.text}")
        return {}

    return resp.json()
