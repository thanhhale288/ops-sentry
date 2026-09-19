from __future__ import annotations

import os

from fastapi import Header, HTTPException

from app.config import settings


def require_ops_token(
    authorization: str | None = Header(default=None),
    x_ops_token: str | None = Header(default=None),
) -> None:
    expected = os.getenv("OPS_API_TOKEN", "").strip() or settings.ops_api_token
    env = (os.getenv("OPS_ENV", "").strip() or settings.ops_env).lower()
    if not expected:
        if env in {"production", "prod"}:
            raise HTTPException(status_code=503, detail="OPS_API_TOKEN required")
        return
    provided = (x_ops_token or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid token")
