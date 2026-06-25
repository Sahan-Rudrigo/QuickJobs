import os
import httpx
from redis_client import get_state, set_state
from whatsapp_api import send_text
import templates

EXPERIENCE_MAP = {"1": "junior", "2": "mid", "3": "senior", "4": "lead"}

UPDATE_FIELD_MAP = {
    "1": ("skills",   "UPDATING_SKILLS"),
    "2": ("location", "UPDATING_LOCATION"),
    "3": ("salary",   "UPDATING_SALARY"),
    "4": ("cv",       "AWAITING_CV_UPDATE"),
    "5": None,
}

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
FILE_SERVICE_URL = os.getenv("FILE_SERVICE_URL", "http://localhost:8002")

_DELETE_KEYWORDS = {"DELETE MY DATA", "DELETE DATA", "ERASE MY DATA", "ERASE DATA"}


def _parse_salary(text: str):
    """Return (salary_min, salary_max) from 'min-max' string, or (None, None)."""
    try:
        parts = text.replace(",", "").replace(" ", "").split("-")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        pass
    return None, None


async def _create_user_profile(phone: str, data: dict) -> None:
    """Create user profile in User Service after onboarding completes."""
    payload = {
        "phone":            phone,
        "name":             data.get("name"),
        "skills":           data.get("skills", []),
        "experience_level": data.get("experience_level"),
        "location":         data.get("location"),
        "salary_min":       data.get("salary_min"),
        "salary_max":       data.get("salary_max"),
        "opt_in_status":    True,
        "onboarding_state": "ACTIVE",
        "availability":     "actively_looking",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{USER_SERVICE_URL}/users", json=payload)
            if resp.status_code == 400:
                await client.patch(f"{USER_SERVICE_URL}/users/{phone}", json=payload)
        print(f"[INFO] User profile created/updated for {phone}")
    except Exception as e:
        print(f"[ERROR] Failed to create user profile for {phone}: {e}")


async def _delete_user_data(phone: str) -> None:
    """
    PDPA right-to-erasure: delete all data for a phone number across services.
    Calls user-service (profile) and file-service (CVs) in parallel.
    Failures are logged but do not block the flow.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            user_del = client.delete(f"{USER_SERVICE_URL}/users/{phone}")
            cv_del   = client.delete(f"{FILE_SERVICE_URL}/cv/{phone}")
            import asyncio
            results = await asyncio.gather(user_del, cv_del, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    print(f"[WARN] Deletion request {i} failed: {r}")
    except Exception as e:
        print(f"[ERROR] Failed to complete data deletion for {phone}: {e}")


async def handle_message(phone: str, text: str):
    state = get_state(phone)
    step  = state["step"]
    data  = state["data"]
    text  = text.strip()

    # ── Global overrides ─────────────────────────────────────────
    if text.upper() == "STOP":
        set_state(phone, "OPTED_OUT", data)
        await send_text(phone, templates.OPT_OUT_CONFIRM)
        return

    if text.upper() == "START":
        set_state(phone, "ACTIVE", data)
        await send_text(phone, templates.OPT_IN_CONFIRM)
        return

    # PDPA deletion request — available from any state
    if text.upper() in _DELETE_KEYWORDS:
        set_state(phone, "CONFIRMING_DELETE", data)
        await send_text(phone, templates.ASK_DELETE_CONFIRM)
        return

    # ── Deletion confirmation state ───────────────────────────────
    if step == "CONFIRMING_DELETE":
        if text.upper() == "CONFIRM DELETE":
            await _delete_user_data(phone)
            set_state(phone, "IDLE", {})
            await send_text(phone, templates.DATA_DELETED_CONFIRM)
        else:
            set_state(phone, "ACTIVE" if data else "IDLE", data)
            await send_text(phone, templates.DATA_DELETE_CANCELLED)
        return

    # ── Onboarding flow ──────────────────────────────────────────

    if step == "IDLE":
        words = set(text.lower().split())
        if words & {"hi", "hello", "register"}:
            set_state(phone, "AWAITING_NAME", data)
            await send_text(phone, templates.WELCOME)

    elif step == "AWAITING_NAME":
        data["name"] = text
        set_state(phone, "AWAITING_SKILLS", data)
        await send_text(phone, templates.ask_skills(data["name"]))

    elif step == "AWAITING_SKILLS":
        data["skills"] = [s.strip() for s in text.split(",") if s.strip()]
        set_state(phone, "AWAITING_EXPERIENCE", data)
        await send_text(phone, templates.ASK_EXPERIENCE)

    elif step == "AWAITING_EXPERIENCE":
        level = EXPERIENCE_MAP.get(text)
        if not level:
            await send_text(phone, templates.INVALID_EXPERIENCE)
            return
        data["experience_level"] = level
        set_state(phone, "AWAITING_LOCATION", data)
        await send_text(phone, templates.ASK_LOCATION)

    elif step == "AWAITING_LOCATION":
        data["location"] = text
        set_state(phone, "AWAITING_SALARY", data)
        await send_text(phone, templates.ASK_SALARY)

    elif step == "AWAITING_SALARY":
        sal_min, sal_max = _parse_salary(text)
        if sal_min is None:
            await send_text(phone, templates.INVALID_SALARY)
            return
        data["salary_min"] = sal_min
        data["salary_max"] = sal_max
        set_state(phone, "AWAITING_CV", data)
        await send_text(phone, templates.ASK_CV)

    elif step == "AWAITING_CV":
        if text == "__CV_UPLOADED__":
            await _create_user_profile(phone, data)
            set_state(phone, "ACTIVE", data)
            await send_text(phone, templates.onboarding_complete(data.get("name", "")))
        else:
            await send_text(phone, templates.ASK_CV)

    # ── Active user menu ─────────────────────────────────────────

    elif step == "ACTIVE":
        if text == "5":
            set_state(phone, "OPTED_OUT", data)
            await send_text(phone, templates.OPT_OUT_CONFIRM)
        elif text in UPDATE_FIELD_MAP and UPDATE_FIELD_MAP[text] is not None:
            field, next_step = UPDATE_FIELD_MAP[text]
            data["_updating_field"] = field
            set_state(phone, next_step, data)
            msg_map = {
                "UPDATING_SKILLS":    templates.ASK_NEW_SKILLS,
                "UPDATING_LOCATION":  templates.ASK_NEW_LOCATION,
                "UPDATING_SALARY":    templates.ASK_NEW_SALARY,
                "AWAITING_CV_UPDATE": templates.ASK_NEW_CV,
            }
            await send_text(phone, msg_map[next_step])
        else:
            await send_text(phone, templates.ACTIVE_MENU)

    # ── Profile update states ─────────────────────────────────────

    elif step == "UPDATING_SKILLS":
        new_skills = [s.strip() for s in text.split(",") if s.strip()]
        data["_pending_value"]   = new_skills
        data["_pending_display"] = ", ".join(new_skills)
        set_state(phone, "CONFIRMING_UPDATE", data)
        await send_text(phone, templates.confirm_update("Skills", data["_pending_display"]))

    elif step == "UPDATING_LOCATION":
        data["_pending_value"]   = text
        data["_pending_display"] = text
        set_state(phone, "CONFIRMING_UPDATE", data)
        await send_text(phone, templates.confirm_update("Location", text))

    elif step == "UPDATING_SALARY":
        sal_min, sal_max = _parse_salary(text)
        if sal_min is None:
            await send_text(phone, templates.INVALID_SALARY)
            return
        data["_pending_value"]   = {"salary_min": sal_min, "salary_max": sal_max}
        data["_pending_display"] = f"LKR {sal_min:,} – {sal_max:,}"
        set_state(phone, "CONFIRMING_UPDATE", data)
        await send_text(phone, templates.confirm_update("Salary", data["_pending_display"]))

    elif step == "AWAITING_CV_UPDATE":
        if text == "__CV_UPLOADED__":
            set_state(phone, "ACTIVE", data)
            await send_text(phone, templates.update_saved("CV"))
        else:
            await send_text(phone, templates.ASK_NEW_CV)

    elif step == "CONFIRMING_UPDATE":
        if text.upper() == "YES":
            field   = data.get("_updating_field")
            value   = data.get("_pending_value")
            display = data.pop("_pending_display", field)

            if field == "skills":
                data["skills"] = value
            elif field == "location":
                data["location"] = value
            elif field == "salary":
                data["salary_min"] = value["salary_min"]
                data["salary_max"] = value["salary_max"]

            data.pop("_updating_field", None)
            data.pop("_pending_value", None)

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.patch(f"{USER_SERVICE_URL}/users/{phone}", json={field: value})
            except Exception as e:
                print(f"[ERROR] Failed to sync update to User Service: {e}")

            set_state(phone, "ACTIVE", data)
            await send_text(phone, templates.update_saved(display))

        elif text.upper() == "NO":
            data.pop("_updating_field", None)
            data.pop("_pending_value", None)
            data.pop("_pending_display", None)
            set_state(phone, "ACTIVE", data)
            await send_text(phone, templates.UPDATE_CANCELLED)
        else:
            field   = data.get("_updating_field", "field")
            display = data.get("_pending_display", "")
            await send_text(phone, templates.confirm_update(field, display))

    elif step == "OPTED_OUT":
        await send_text(phone, "You are unsubscribed. Send *START* to re-subscribe.")
