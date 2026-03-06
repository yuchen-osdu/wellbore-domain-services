import json
from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.conf import Config


def _build_full_server_url(base_url: str, openapi_prefix: str) -> str:
    # Starlette/FastAPI may already include the root path in base_url when running
    # behind a reverse proxy (for us: /api/os-wellbore-ddms).
    base_url = base_url.rstrip("/")
    prefix = openapi_prefix.rstrip("/")
    if not prefix:
        return base_url
    # Avoid duplicating the prefix in OpenAPI servers.url. Without this guard,
    # Swagger UI can produce request URLs such as .../api/.../api/.../about.
    if base_url.endswith(prefix):
        return base_url
    # In setups where base_url does not include the service prefix, append it once.
    return f"{base_url}{prefix}"


class OpenAPIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path.endswith("/openapi.json"):
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            schema = json.loads(body.decode('utf-8'))
            base_url = str(request.base_url)
            full_url = _build_full_server_url(base_url, Config.openapi_prefix.value)
            schema["servers"] = [{"url": full_url}]
            return JSONResponse(schema)
        return response
