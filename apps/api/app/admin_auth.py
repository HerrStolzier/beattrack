import hmac
import os

from fastapi import HTTPException


def verify_admin(authorization: str | None) -> None:
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret:
        raise HTTPException(503, "ADMIN_SECRET not configured")

    provided = (authorization or "").removeprefix("Bearer ")
    if not hmac.compare_digest(provided.encode(), admin_secret.encode()):
        raise HTTPException(403, "Unauthorized")
