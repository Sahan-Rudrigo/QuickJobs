import httpx
import os


async def send_text(to: str, message: str):
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    token = os.getenv("WHATSAPP_TOKEN")
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"

    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
        )
