"""
Notification Service — unit tests.
All external I/O (Redis, SQS, Meta API) is mocked.
"""
import pytest
from unittest.mock import patch, MagicMock, call


# ── Helpers imported after mocking Redis ─────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_redis_client():
    """Prevent real Redis connection on import."""
    with patch("redis.from_url") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_boto_client():
    with patch("boto3.client") as mock:
        yield mock


def _fresh_consumer():
    """Re-import consumer after patching so module-level Redis/SQS are mocked."""
    import importlib
    import sqs_consumer
    importlib.reload(sqs_consumer)
    return sqs_consumer


# ── _is_opted_in ─────────────────────────────────────────────────────────────

def test_is_opted_in_returns_true_when_key_missing(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._redis.get.return_value = None
    assert m._is_opted_in("94771234567") is True


def test_is_opted_in_returns_false_when_opted_out(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._redis.get.return_value = "false"
    assert m._is_opted_in("94771234567") is False


def test_is_opted_in_returns_true_when_opted_in(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._redis.get.return_value = "true"
    assert m._is_opted_in("94771234567") is True


# ── Deduplication ─────────────────────────────────────────────────────────────

def test_already_notified_returns_false_when_key_missing(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._redis.get.return_value = None
    assert m._already_notified("job-1", "94771234567") is False


def test_already_notified_returns_true_when_key_set(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._redis.get.return_value = "1"
    assert m._already_notified("job-1", "94771234567") is True


def test_mark_notified_sets_redis_key_with_ttl(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m._mark_notified("job-1", "94771234567")
    m._redis.setex.assert_called_once()
    args = m._redis.setex.call_args[0]
    assert args[0] == "notified:job-1:94771234567"
    assert args[1] > 0        # TTL is set
    assert args[2] == "1"


# ── _build_message ────────────────────────────────────────────────────────────

def test_build_message_includes_all_fields(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    msg = m._build_message("Senior Dev", "Acme", "Colombo", "Full-time", "LKR 100k")
    assert "Senior Dev" in msg
    assert "Acme" in msg
    assert "Colombo" in msg
    assert "Full-time" in msg
    assert "LKR 100k" in msg


def test_build_message_omits_missing_optional_fields(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    msg = m._build_message("Dev", "Acme", "", "", "")
    assert "Acme" in msg
    # Should not have dangling empty lines for location/type/salary
    assert "📍" not in msg
    assert "💼" not in msg
    assert "💰" not in msg


# ── _send_whatsapp ────────────────────────────────────────────────────────────

def test_send_whatsapp_skips_when_no_credentials(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = ""
    m.WHATSAPP_PHONE_ID = ""
    result = m._send_whatsapp("94771234567", "Hello")
    assert result is False


@patch("httpx.post")
def test_send_whatsapp_returns_true_on_success(mock_post, mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "test-token"
    m.WHATSAPP_PHONE_ID = "12345"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    result = m._send_whatsapp("94771234567", "Hello")
    assert result is True


@patch("httpx.post")
def test_send_whatsapp_returns_false_on_api_error(mock_post, mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "test-token"
    m.WHATSAPP_PHONE_ID = "12345"

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    mock_post.return_value = mock_resp

    result = m._send_whatsapp("94771234567", "Hello")
    assert result is False


@patch("httpx.post", side_effect=Exception("timeout"))
def test_send_whatsapp_returns_false_on_exception(mock_post, mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "test-token"
    m.WHATSAPP_PHONE_ID = "12345"
    result = m._send_whatsapp("94771234567", "Hello")
    assert result is False


# ── process_job_matched ───────────────────────────────────────────────────────

@patch("httpx.post")
def test_process_job_matched_sends_to_opted_in(mock_post, mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "tok"
    m.WHATSAPP_PHONE_ID = "pid"
    m._redis.get.side_effect = lambda key: (
        None if key.startswith("opt_in:")
        else None  # not yet notified
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp

    m.process_job_matched({
        "job_id": "job-1", "job_title": "Dev", "company_name": "Acme",
        "location": "Colombo", "job_type": "Full-time", "salary": "LKR 100k",
        "matched_phones": ["94771111111", "94772222222"],
    })
    assert mock_post.call_count == 2


def test_process_job_matched_skips_opted_out(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "tok"
    m.WHATSAPP_PHONE_ID = "pid"

    def redis_get(key):
        if key.startswith("opt_in:"):
            return "false"
        return None

    m._redis.get.side_effect = redis_get

    with patch.object(m, "_send_whatsapp") as mock_send:
        m.process_job_matched({
            "job_id": "job-1", "job_title": "Dev", "company_name": "Acme",
            "location": "", "job_type": "", "salary": "",
            "matched_phones": ["94771111111"],
        })
        mock_send.assert_not_called()


def test_process_job_matched_skips_already_notified(mock_redis_client, mock_boto_client):
    """Candidate already notified for this job must not receive a duplicate."""
    m = _fresh_consumer()
    m.WHATSAPP_TOKEN    = "tok"
    m.WHATSAPP_PHONE_ID = "pid"

    def redis_get(key):
        if key.startswith("notified:"):
            return "1"   # already notified
        return None      # opted in

    m._redis.get.side_effect = redis_get

    with patch.object(m, "_send_whatsapp") as mock_send:
        m.process_job_matched({
            "job_id": "job-1", "job_title": "Dev", "company_name": "Acme",
            "location": "", "job_type": "", "salary": "",
            "matched_phones": ["94771111111"],
        })
        mock_send.assert_not_called()


def test_process_job_matched_empty_phones(mock_redis_client, mock_boto_client):
    m = _fresh_consumer()
    with patch.object(m, "_send_whatsapp") as mock_send:
        m.process_job_matched({
            "job_id": "job-1", "job_title": "Dev", "company_name": "Acme",
            "location": "", "job_type": "", "salary": "",
            "matched_phones": [],
        })
        mock_send.assert_not_called()
