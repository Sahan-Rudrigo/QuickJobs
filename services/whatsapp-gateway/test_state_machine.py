"""
Unit tests for state_machine.py — WhatsApp conversation flow.

All external I/O is mocked:
  - redis_client.get_state / set_state
  - whatsapp_api.send_text
  - httpx.AsyncClient (user-service and file-service HTTP calls)
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, call


# ── Helpers ───────────────────────────────────────────────────────────

def run(coro):
    """Run an async coroutine in a sync test (compatible with Python 3.10+)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def make_mocks(step="IDLE", data=None):
    """Return (get_state mock, set_state mock, send_text mock) for a given state."""
    state = {"step": step, "data": data or {}}
    mock_get  = MagicMock(return_value=state)
    mock_set  = MagicMock()
    mock_send = AsyncMock()
    return mock_get, mock_set, mock_send


def drive(phone, text, step="IDLE", data=None, http_responses=None):
    """
    Call handle_message with mocked dependencies.
    Returns (set_state calls, send_text calls).
    """
    mock_get, mock_set, mock_send = make_mocks(step, data)

    patches = [
        patch("state_machine.get_state", mock_get),
        patch("state_machine.set_state", mock_set),
        patch("state_machine.send_text", mock_send),
    ]

    if http_responses is not None:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        for method, url_fragment, response in (http_responses or []):
            getattr(mock_client, method).return_value = response
        patches.append(patch("state_machine.httpx.AsyncClient", return_value=mock_client))

    from state_machine import handle_message
    with patches[0], patches[1], patches[2]:
        if len(patches) > 3:
            with patches[3]:
                run(handle_message(phone, text))
        else:
            run(handle_message(phone, text))

    return mock_set.call_args_list, mock_send.call_args_list


# ── Global overrides (work from any state) ────────────────────────────

def test_stop_from_idle():
    set_calls, send_calls = drive("94771234567", "STOP", step="IDLE")
    assert any("OPTED_OUT" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_stop_from_active():
    set_calls, send_calls = drive("94771234567", "STOP", step="ACTIVE")
    assert any("OPTED_OUT" in str(c) for c in set_calls)


def test_start_from_opted_out():
    set_calls, send_calls = drive("94771234567", "START", step="OPTED_OUT")
    assert any("ACTIVE" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_delete_keyword_any_state():
    set_calls, send_calls = drive("94771234567", "DELETE MY DATA", step="ACTIVE")
    assert any("CONFIRMING_DELETE" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_delete_keyword_variants():
    for keyword in ("DELETE DATA", "ERASE MY DATA", "ERASE DATA"):
        set_calls, _ = drive("94771234567", keyword, step="IDLE")
        assert any("CONFIRMING_DELETE" in str(c) for c in set_calls), f"Failed for: {keyword}"


# ── Job-offer APPLY / SKIP ─────────────────────────────────────────────

def _drive_offer(text, step="ACTIVE", data=None, pending_offer=None, next_offer=None, patch_status=200):
    """Like drive(), but also mocks peek/pop_pending_offer and the PATCH decision call."""
    mock_get  = MagicMock(return_value={"step": step, "data": data or {}})
    mock_set  = MagicMock()
    mock_send = AsyncMock()
    mock_peek = MagicMock(side_effect=[pending_offer, next_offer])
    mock_pop  = MagicMock(return_value=pending_offer)

    mock_resp = MagicMock(status_code=patch_status)
    mock_resp.json.return_value = {"status": "APPLIED", "job_title": "Dev", "company_name": "Acme"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.patch = AsyncMock(return_value=mock_resp)

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.peek_pending_offer", mock_peek), \
         patch("state_machine.pop_pending_offer", mock_pop), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", text))

    return mock_set, mock_send, mock_client


def test_apply_with_pending_offer_resolves_and_does_not_touch_state():
    offer = {"job_id": "job-1", "job_title": "Dev", "company_name": "Acme"}
    mock_set, mock_send, mock_client = _drive_offer("APPLY", step="ACTIVE", pending_offer=offer)

    mock_client.patch.assert_called_once()
    url = str(mock_client.patch.call_args)
    assert "job-1" in url and "94771234567" in url
    assert mock_client.patch.call_args.kwargs["json"] == {"decision": "APPLY"}
    mock_set.assert_not_called()  # must resume whatever step the user was in
    assert len(mock_send.call_args_list) == 1


def test_skip_with_pending_offer_resolves():
    offer = {"job_id": "job-1", "job_title": "Dev", "company_name": "Acme"}
    mock_set, mock_send, mock_client = _drive_offer("SKIP", step="IDLE", pending_offer=offer)

    assert mock_client.patch.call_args.kwargs["json"] == {"decision": "SKIP"}
    mock_set.assert_not_called()


def test_apply_no_pending_offer_falls_through_to_normal_dispatch():
    """A stray APPLY with nothing pending must not silently do nothing."""
    mock_set, mock_send, mock_client = _drive_offer("APPLY", step="ACTIVE", pending_offer=None)
    mock_client.patch.assert_not_called()
    assert len(mock_send.call_args_list) == 1  # falls through to ACTIVE_MENU


def test_apply_with_second_offer_queued_sends_next_offer_prompt():
    offer = {"job_id": "job-1", "job_title": "Dev", "company_name": "Acme"}
    next_offer = {"job_id": "job-2", "job_title": "QA", "company_name": "Beta"}
    _, mock_send, _ = _drive_offer("APPLY", step="ACTIVE", pending_offer=offer, next_offer=next_offer)
    assert len(mock_send.call_args_list) == 2
    assert "QA" in str(mock_send.call_args_list[1])


# ── PDPA deletion confirmation ─────────────────────────────────────────

def test_confirm_delete_triggers_deletion():
    """CONFIRM DELETE → calls both user-service and file-service deletes."""
    mock_get  = MagicMock(return_value={"step": "CONFIRMING_DELETE", "data": {}})
    mock_set  = MagicMock()
    mock_send = AsyncMock()
    mock_resp = MagicMock(status_code=200)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.delete = AsyncMock(return_value=mock_resp)

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", "CONFIRM DELETE"))

    assert mock_client.delete.call_count == 2
    urls_called = [str(c) for c in mock_client.delete.call_args_list]
    assert any("users" in u for u in urls_called)
    assert any("/cv/" in u for u in urls_called)
    assert any("IDLE" in str(c) for c in mock_set.call_args_list)


def test_cancel_delete_returns_to_active():
    set_calls, send_calls = drive(
        "94771234567", "no thanks", step="CONFIRMING_DELETE",
        data={"name": "Lakshan"}
    )
    assert any("ACTIVE" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_cancel_delete_idle_when_no_data():
    set_calls, _ = drive("94771234567", "nope", step="CONFIRMING_DELETE", data={})
    assert any("IDLE" in str(c) for c in set_calls)


# ── Onboarding flow ───────────────────────────────────────────────────

def test_idle_hello_triggers_welcome():
    # "start" is a global override (→ ACTIVE), not an onboarding trigger
    for greeting in ("hi", "hello", "register"):
        set_calls, send_calls = drive("94771234567", greeting, step="IDLE")
        assert any("AWAITING_NAME" in str(c) for c in set_calls), f"Failed for: {greeting}"
        assert len(send_calls) == 1


def test_idle_start_goes_to_active_not_onboarding():
    """START is a global override — must go to ACTIVE, not start onboarding."""
    set_calls, send_calls = drive("94771234567", "start", step="IDLE")
    assert any("ACTIVE" in str(c) for c in set_calls)
    assert not any("AWAITING_NAME" in str(c) for c in set_calls)


def test_idle_unknown_no_response():
    # "what is this" contains "hi" as a substring in "this" — must NOT trigger
    for msg in ("what is this", "history", "this is me", "not registered"):
        set_calls, send_calls = drive("94771234567", msg, step="IDLE")
        assert len(send_calls) == 0, f"Falsely triggered for: {msg}"


def test_awaiting_name_stores_name():
    set_calls, send_calls = drive("94771234567", "Lakshan", step="AWAITING_NAME")
    assert any("AWAITING_SKILLS" in str(c) for c in set_calls)
    assert any("Lakshan" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_awaiting_skills_parses_comma_separated():
    set_calls, send_calls = drive("94771234567", "Python, React, SQL", step="AWAITING_SKILLS")
    assert any("AWAITING_EXPERIENCE" in str(c) for c in set_calls)
    set_data = set_calls[0][0][2]
    assert set_data["skills"] == ["Python", "React", "SQL"]


def test_awaiting_experience_valid_choice():
    for choice, level in [("1", "junior"), ("2", "mid"), ("3", "senior"), ("4", "lead")]:
        set_calls, _ = drive("94771234567", choice, step="AWAITING_EXPERIENCE")
        assert any("AWAITING_LOCATION" in str(c) for c in set_calls)
        set_data = set_calls[0][0][2]
        assert set_data["experience_level"] == level


def test_awaiting_experience_invalid_re_prompts():
    set_calls, send_calls = drive("94771234567", "5", step="AWAITING_EXPERIENCE")
    assert len(set_calls) == 0  # state unchanged
    assert len(send_calls) == 1


def test_awaiting_location_stores_location():
    set_calls, _ = drive("94771234567", "Colombo", step="AWAITING_LOCATION")
    assert any("AWAITING_SALARY" in str(c) for c in set_calls)
    assert set_calls[0][0][2]["location"] == "Colombo"


def test_awaiting_salary_valid_format():
    set_calls, _ = drive("94771234567", "50000-80000", step="AWAITING_SALARY")
    assert any("AWAITING_CV" in str(c) for c in set_calls)
    data = set_calls[0][0][2]
    assert data["salary_min"] == 50000
    assert data["salary_max"] == 80000


def test_awaiting_salary_invalid_re_prompts():
    set_calls, send_calls = drive("94771234567", "lots of money", step="AWAITING_SALARY")
    assert len(set_calls) == 0
    assert len(send_calls) == 1


def test_awaiting_cv_uploaded_completes_onboarding():
    """__CV_UPLOADED__ sentinel advances to ACTIVE and creates user profile."""
    mock_resp = MagicMock(status_code=201)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.post  = AsyncMock(return_value=mock_resp)
    mock_client.patch = AsyncMock(return_value=mock_resp)

    mock_get  = MagicMock(return_value={"step": "AWAITING_CV", "data": {"name": "Lakshan"}})
    mock_set  = MagicMock()
    mock_send = AsyncMock()

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", "__CV_UPLOADED__"))

    assert any("ACTIVE" in str(c) for c in mock_set.call_args_list)
    mock_client.post.assert_called_once()
    assert len(mock_send.call_args_list) == 1


def test_awaiting_cv_non_cv_message_re_prompts():
    set_calls, send_calls = drive("94771234567", "where do I send the CV?", step="AWAITING_CV")
    assert len(set_calls) == 0
    assert len(send_calls) == 1


# ── Active menu ───────────────────────────────────────────────────────

def test_active_unknown_message_shows_menu():
    set_calls, send_calls = drive("94771234567", "hello?", step="ACTIVE")
    assert len(send_calls) == 1


def test_active_option_5_opts_out():
    set_calls, _ = drive("94771234567", "5", step="ACTIVE")
    assert any("OPTED_OUT" in str(c) for c in set_calls)


def test_active_option_1_enters_skill_update():
    set_calls, _ = drive("94771234567", "1", step="ACTIVE")
    assert any("UPDATING_SKILLS" in str(c) for c in set_calls)


def test_active_option_2_enters_location_update():
    set_calls, _ = drive("94771234567", "2", step="ACTIVE")
    assert any("UPDATING_LOCATION" in str(c) for c in set_calls)


def _drive_applications(text, status_code=200, json_body=None):
    mock_get  = MagicMock(return_value={"step": "ACTIVE", "data": {}})
    mock_set  = MagicMock()
    mock_send = AsyncMock()

    mock_resp = MagicMock(status_code=status_code)
    mock_resp.json.return_value = json_body or []
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", text))

    return mock_set, mock_send, mock_client


def test_active_option_6_lists_applications():
    mock_set, mock_send, mock_client = _drive_applications(
        "6", json_body=[{"job_id": "job-1", "title": "Dev", "company_name": "Acme", "location": "Colombo", "salary": "100k"}]
    )
    mock_client.get.assert_called_once()
    assert "status=APPLIED" in str(mock_client.get.call_args) or mock_client.get.call_args.kwargs.get("params") == {"status": "APPLIED"}
    mock_set.assert_not_called()
    assert "Dev" in str(mock_send.call_args_list[0])


def test_active_option_7_with_rejected_jobs_enters_viewing_step():
    mock_set, mock_send, _ = _drive_applications(
        "7", json_body=[{"job_id": "job-1", "title": "Dev", "company_name": "Acme", "location": None, "salary": None}]
    )
    assert any("VIEWING_REJECTED" in str(c) for c in mock_set.call_args_list)
    set_data = mock_set.call_args_list[0][0][2]
    assert set_data["_rejected_job_ids"] == ["job-1"]


def test_active_option_7_no_rejected_jobs():
    mock_set, mock_send, _ = _drive_applications("7", json_body=[])
    mock_set.assert_not_called()
    assert len(mock_send.call_args_list) == 1


def test_viewing_rejected_valid_choice_reapplies():
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"status": "APPLIED", "job_title": "Dev", "company_name": "Acme"}
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.patch = AsyncMock(return_value=mock_resp)

    mock_get  = MagicMock(return_value={"step": "VIEWING_REJECTED", "data": {"_rejected_job_ids": ["job-1", "job-2"]}})
    mock_set  = MagicMock()
    mock_send = AsyncMock()

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", "2"))

    mock_client.patch.assert_called_once()
    assert "job-2" in str(mock_client.patch.call_args)
    assert any("ACTIVE" in str(c) for c in mock_set.call_args_list)
    set_data = mock_set.call_args_list[0][0][2]
    assert "_rejected_job_ids" not in set_data


def test_viewing_rejected_invalid_choice_reprompts():
    set_calls, send_calls = drive(
        "94771234567", "9", step="VIEWING_REJECTED", data={"_rejected_job_ids": ["job-1"]}
    )
    assert len(set_calls) == 0
    assert len(send_calls) == 1


# ── Profile update flow ───────────────────────────────────────────────

def test_updating_skills_asks_confirmation():
    set_calls, send_calls = drive(
        "94771234567", "Python, Go, Rust", step="UPDATING_SKILLS",
        data={"_updating_field": "skills"}
    )
    assert any("CONFIRMING_UPDATE" in str(c) for c in set_calls)
    assert len(send_calls) == 1


def test_confirming_update_yes_saves_and_patches():
    """YES in CONFIRMING_UPDATE syncs to user-service and returns to ACTIVE."""
    mock_resp = MagicMock(status_code=200)
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    mock_client.patch = AsyncMock(return_value=mock_resp)

    data = {
        "_updating_field": "skills",
        "_pending_value": ["Go", "Rust"],
        "_pending_display": "Go, Rust",
    }

    mock_get  = MagicMock(return_value={"step": "CONFIRMING_UPDATE", "data": data})
    mock_set  = MagicMock()
    mock_send = AsyncMock()

    from state_machine import handle_message
    with patch("state_machine.get_state", mock_get), \
         patch("state_machine.set_state", mock_set), \
         patch("state_machine.send_text", mock_send), \
         patch("state_machine.httpx.AsyncClient", return_value=mock_client):
        run(handle_message("94771234567", "YES"))

    assert any("ACTIVE" in str(c) for c in mock_set.call_args_list)
    mock_client.patch.assert_called_once()


def test_confirming_update_no_cancels():
    set_calls, send_calls = drive(
        "94771234567", "NO", step="CONFIRMING_UPDATE",
        data={"_updating_field": "skills", "_pending_value": ["Go"], "_pending_display": "Go"}
    )
    assert any("ACTIVE" in str(c) for c in set_calls)
    assert len(send_calls) == 1
