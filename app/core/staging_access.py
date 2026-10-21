"""Protect staging routes from unauthenticated public access."""
import hmac
import os

from fastapi.responses import JSONResponse


async def staging_access_middleware(request, call_next):
    if os.environ.get("APP_ENV", "").lower() != "staging":
        return await call_next(request)
    # Quo authenticates separately using signed webhook headers.
    if request.url.path == "/api/v1/webhooks/quo":
        return await call_next(request)
    token = os.environ.get("STAGING_ACCESS_TOKEN", "")
    if not token:
        return JSONResponse({"detail": "Staging access not configured"}, status_code=503)
    supplied = request.headers.get("X-Staging-Token", "")
    if not hmac.compare_digest(supplied, token):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)
