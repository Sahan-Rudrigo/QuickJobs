from fastapi import FastAPI, Request, Query
from dotenv import load_dotenv
from state_machine import handle_message
import os
import traceback

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "quickjobs_verify_123")


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return {"error": "verification failed"}


@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            phone = msg["from"]
            msg_type = msg.get("type", "")

            if msg_type == "text":
                text = msg["text"]["body"]
                await handle_message(phone, text)
            elif msg_type == "document":
                await handle_message(phone, "__CV_UPLOADED__")

    except Exception as e:
        print("ERROR:", traceback.format_exc())

    return {"status": "ok"}


@app.get("/")
async def health():
    return {"status": "WhatsApp Gateway is running"}
