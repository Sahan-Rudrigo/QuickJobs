import redis
import json
import os

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


def get_state(phone: str) -> dict:
    data = r.get(f"state:{phone}")
    if data:
        return json.loads(data)
    return {"step": "IDLE", "data": {}}


def set_state(phone: str, step: str, data: dict = {}):
    r.set(f"state:{phone}", json.dumps({"step": step, "data": data}), ex=86400)


def clear_state(phone: str):
    r.delete(f"state:{phone}")
