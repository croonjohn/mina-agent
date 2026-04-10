"""API Key authentication middleware."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional

from app.core.config import get_settings

# Paths that always skip API key auth (docs, health, root)
_PUBLIC_PATHS = frozenset({
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/health",
})

# Path prefixes that REQUIRE API key auth (external services calling in)
_PROTECTED_PREFIXES = (
    "/api/v1/devvit",
)

_AUTH_ERROR_DETAIL = "Invalid or missing API key. Provide Authorization: Bearer <key> or X-API-Key: <key>"


def _check_api_key(request: Request) -> bool:
    """Check if the request has a valid API key. Returns True if valid."""
    settings = get_settings()
    expected = settings.api_secret_key

    # Try Authorization: Bearer <key>
    auth_header: Optional[str] = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token == expected:
            return True

    # Try X-API-Key header
    api_key_header: Optional[str] = request.headers.get("x-api-key")
    if api_key_header and api_key_header.strip() == expected:
        return True

    return False


async def verify_api_key(request: Request) -> str:
    """
    FastAPI dependency that verifies the API key from either:
      - Authorization: Bearer <key>
      - X-API-Key: <key>

    Returns the validated key on success, raises 401 on failure.
    Can be used as Depends(verify_api_key) on individual routes.
    """
    if _check_api_key(request):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return request.headers.get("x-api-key", "").strip()

    raise HTTPException(status_code=401, detail=_AUTH_ERROR_DETAIL)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces API key auth on all /api/v1/ routes
    except public paths and Devvit endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Skip OPTIONS (CORS preflight) unconditionally
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public paths (docs, health, root)
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)

        # Only ENFORCE auth on protected prefixes (e.g. /api/v1/devvit/*)
        # All other /api/v1/* endpoints are internal dashboard access -- no key needed.
        is_protected = any(path.startswith(prefix) for prefix in _PROTECTED_PREFIXES)
        if is_protected:
            if _check_api_key(request):
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={"detail": _AUTH_ERROR_DETAIL},
            )

        # Internal /api/v1/* routes: allow without API key
        return await call_next(request)
