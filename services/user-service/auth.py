import time
import os
import httpx
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError

COGNITO_REGION  = os.getenv("COGNITO_REGION",  "ap-south-1")
COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID", "ap-south-1_0qt4DZnx6")
SKIP_AUTH       = os.getenv("SKIP_AUTH", "false").lower() == "true"

_jwks_cache:      dict  = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600


def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache and (time.time() - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    url = (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com"
        f"/{COGNITO_POOL_ID}/.well-known/jwks.json"
    )
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    _jwks_cache      = resp.json()
    _jwks_fetched_at = time.time()
    return _jwks_cache


def get_token_payload(authorization: str = Header(default="")) -> dict:
    if SKIP_AUTH:
        return {
            "sub": "dev-user",
            "cognito:groups": ["quickjobs-admins", "quickjobs-employers"],
        }

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization[7:]
    try:
        jwks   = _fetch_jwks()
        header = jwt.get_unverified_header(token)
        key    = next(
            (k for k in jwks["keys"] if k["kid"] == header.get("kid")), None
        )
        if not key:
            raise HTTPException(status_code=401, detail="Token key not found in JWKS")
        payload = jwt.decode(
            token, key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Auth error: {exc}")


def require_admin(payload: dict = Depends(get_token_payload)) -> dict:
    if "quickjobs-admins" not in payload.get("cognito:groups", []):
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload
