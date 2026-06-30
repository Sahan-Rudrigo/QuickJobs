from fastapi import FastAPI, Request, Query
from dotenv import load_dotenv
from state_machine import handle_message
from whatsapp_api import download_media, forward_cv_to_file_service, send_text
from redis_client import get_state
import os
import traceback
import templates

load_dotenv()

app = FastAPI(title="QuickJobs WhatsApp Gateway")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "quickjobs_verify_123")


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return {"error": "verification failed"}


@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry   = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value   = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        msg      = messages[0]
        phone    = msg["from"]
        msg_type = msg.get("type", "")

        if msg_type == "text":
            text = msg["text"]["body"]
            await handle_message(phone, text)

        elif msg_type in ("document", "image"):
            # Get media_id from the correct field
            media_data = msg.get(msg_type, {})
            media_id   = media_data.get("id")

            if not media_id:
                await send_text(phone, "❌ We couldn't receive your file. Please try sending it again.")
                return {"status": "ok"}

            # Download file from Meta
            file_bytes, mime_type, filename = await download_media(media_id)

            # Get user's current profile data from Redis state
            state      = get_state(phone)
            user_data  = state.get("data", {})
            skills     = user_data.get("skills", [])
            experience = user_data.get("experience_level", "")

            # Forward to File Service — only advance state machine on success
            result = await forward_cv_to_file_service(
                phone=phone,
                file_bytes=file_bytes,
                filename=filename,
                mime_type=mime_type,
                skills=skills,
                experience=experience,
            )

            if not result:
                await send_text(phone, templates.CV_UPLOAD_FAILED)
                return {"status": "ok"}

            await handle_message(phone, "__CV_UPLOADED__")

    except Exception:
        print("ERROR:", traceback.format_exc())

    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "whatsapp-gateway", "port": 8000}


@app.get("/")
async def root():
    return {"service": "QuickJobs WhatsApp Gateway"}
