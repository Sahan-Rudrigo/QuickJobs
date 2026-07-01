import os
import httpx
from redis_client import get_state, set_state, peek_pending_offer, pop_pending_offer
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

USER_SERVICE_URL    = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
FILE_SERVICE_URL    = os.getenv("FILE_SERVICE_URL", "http://localhost:8002")
COMPANY_SERVICE_URL = os.getenv("COMPANY_SERVICE_URL", "http://localhost:8003")

_DELETE_KEYWORDS   = {"DELETE MY DATA", "DELETE DATA", "ERASE MY DATA", "ERASE DATA"}
_RESTART_TRIGGERS  = {"hi", "hello", "register", "restart"}


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
            if resp.status_code == 201:
                print(f"[INFO] User profile created for {phone}")
            elif resp.status_code == 400:
                patch = await client.patch(f"{USER_SERVICE_URL}/users/{phone}", json=payload)
                if patch.status_code == 200:
                    print(f"[INFO] User profile updated for {phone}")
                else:
                    print(f"[ERROR] PATCH /users/{phone} returned {patch.status_code}: {patch.text}")
            else:
                print(f"[ERROR] POST /users returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to create user profile for {phone}: {e}")


async def _resolve_offer(phone: str, job_id: str, decision: str) -> dict:
    """
    Flip a JobApplication's status via Company Service.
    Returns the response JSON (job_title, company_name, status) or {} on failure.
    Used both for an immediate APPLY/SKIP reply and for the reapply flow.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(
                f"{COMPANY_SERVICE_URL}/jobs/{job_id}/applicants/{phone}",
                json={"decision": decision},
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"[ERROR] resolve_offer {job_id}/{phone} returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to resolve offer for {phone}, job {job_id}: {e}")
    return {}


async def _fetch_applications(phone: str, status: str) -> list:
    """Fetch a candidate's jobs by status (APPLIED or REJECTED) from Company Service."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{COMPANY_SERVICE_URL}/candidates/{phone}/applications",
                params={"status": status},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch {status} applications for {phone}: {e}")
    return []


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

    # ── Global restart ────────────────────────────────────────────
    # "hi / hello / register / restart" restarts onboarding from any state,
    # matching what every template advertises ("RESTART — Re-register from the beginning")
    if set(text.lower().split()) & _RESTART_TRIGGERS:
        set_state(phone, "AWAITING_NAME", {})
        await send_text(phone, templates.WELCOME)
        return

    # ── Job-offer APPLY / SKIP override ───────────────────────────
    # Must NOT call set_state — resumes whatever step the user was already in.
    if text.upper() in ("APPLY", "SKIP"):
        offer = peek_pending_offer(phone)
        if offer:
            pop_pending_offer(phone)
            decision = "APPLY" if text.upper() == "APPLY" else "SKIP"
            result = await _resolve_offer(phone, offer["job_id"], decision)
            await send_text(phone, templates.offer_resolved(decision, result))

            next_offer = peek_pending_offer(phone)
            if next_offer:
                await send_text(phone, templates.next_offer_waiting(next_offer["job_title"], next_offer["company_name"]))
            return
        # no pending offer: fall through to normal step dispatch below —
        # a stray "apply"/"skip" with nothing pending must not do nothing.

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
        # restart triggers already handled above — any other message gets a guide
        await send_text(phone, templates.IDLE_PROMPT)

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
        elif text == "6":
            apps = await _fetch_applications(phone, "APPLIED")
            await send_text(phone, templates.applications_list(apps))
        elif text == "7":
            rejected = await _fetch_applications(phone, "REJECTED")
            if not rejected:
                await send_text(phone, templates.NO_REJECTED_JOBS)
            else:
                data["_rejected_job_ids"] = [j["job_id"] for j in rejected]
                set_state(phone, "VIEWING_REJECTED", data)
                await send_text(phone, templates.rejected_jobs_list(rejected))
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

    elif step == "VIEWING_REJECTED":
        ids = data.get("_rejected_job_ids", [])
        idx = int(text) - 1 if text.isdigit() else -1
        if not (0 <= idx < len(ids)):
            await send_text(phone, templates.INVALID_LIST_CHOICE)
            return
        result = await _resolve_offer(phone, ids[idx], "APPLY")  # reapply = APPLY on a REJECTED row
        data.pop("_rejected_job_ids", None)
        set_state(phone, "ACTIVE", data)
        if result:
            await send_text(phone, templates.reapplied_confirm(result["job_title"], result["company_name"]))
        else:
            await send_text(phone, templates.REAPPLY_FAILED)

    elif step == "OPTED_OUT":
        await send_text(phone, "You are unsubscribed. Send *START* to re-subscribe.")
