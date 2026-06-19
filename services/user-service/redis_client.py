import redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Single Redis connection used across the service
r = redis.from_url(REDIS_URL, decode_responses=True)


def set_opt_in_status(phone: str, status: bool):
    """
    Save opt-in status to Redis for fast lookup.
    Key format: opt_in:{phone}
    Value: "true" or "false"

    Called every time user opts in or opts out.
    Notification Service reads this before sending any WhatsApp message.
    """
    r.set(f"opt_in:{phone}", "true" if status else "false")


def get_opt_in_status(phone: str) -> bool:
    """
    Read opt-in status from Redis.
    Returns True if user wants alerts.
    Returns True if key not found (default to opted in).
    """
    value = r.get(f"opt_in:{phone}")
    if value is None:
        return True  # default: opted in
    return value == "true"


def delete_opt_in_status(phone: str):
    """
    Remove opt-in key from Redis.
    Called when a user profile is deleted (PDPA compliance).
    """
    r.delete(f"opt_in:{phone}")


def ping() -> bool:
    """
    Check if Redis connection is alive.
    Used in health check endpoint.
    """
    try:
        return r.ping()
    except Exception:
        return False
