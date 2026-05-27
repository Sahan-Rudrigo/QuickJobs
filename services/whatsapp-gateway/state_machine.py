from redis_client import get_state, set_state
from whatsapp_api import send_text


async def handle_message(phone: str, text: str):
    state = get_state(phone)
    step = state["step"]
    data = state["data"]

    if step == "IDLE":
        if "hi" in text.lower() or "register" in text.lower() or "hello" in text.lower():
            set_state(phone, "AWAITING_NAME")
            await send_text(phone, "Welcome to QuickJobs!\nWhat is your full name?")

    elif step == "AWAITING_NAME":
        data["name"] = text.strip()
        set_state(phone, "AWAITING_SKILLS", data)
        await send_text(phone, f"Nice to meet you, {data['name']}!\nWhat are your main skills? (e.g. Python, React, SQL)")

    elif step == "AWAITING_SKILLS":
        data["skills"] = [s.strip() for s in text.split(",")]
        set_state(phone, "AWAITING_EXPERIENCE", data)
        await send_text(phone, "What is your experience level?\n1. Junior\n2. Mid\n3. Senior\n4. Lead\n\nReply with the number.")

    elif step == "AWAITING_EXPERIENCE":
        level_map = {"1": "junior", "2": "mid", "3": "senior", "4": "lead"}
        data["experience_level"] = level_map.get(text.strip(), "junior")
        set_state(phone, "AWAITING_LOCATION", data)
        await send_text(phone, "What city or region are you based in?")

    elif step == "AWAITING_LOCATION":
        data["location"] = text.strip()
        set_state(phone, "AWAITING_CV", data)
        await send_text(phone, "Almost done! Please send your CV as a PDF or Word file.")

    elif step == "AWAITING_CV":
        set_state(phone, "ACTIVE", data)
        await send_text(phone, f"You are all set, {data.get('name', '')}! We will notify you when a matching job appears.")

    elif step == "ACTIVE":
        if text.strip() == "5":
            set_state(phone, "IDLE", {})
            await send_text(phone, "You have been unsubscribed from job alerts. Send 'hi' anytime to register again.")
        elif text.strip().upper() == "START":
            set_state(phone, "ACTIVE", data)
            await send_text(phone, "Welcome back! You will now receive job alerts again.")
