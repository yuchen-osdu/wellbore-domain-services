from fastapi import Request
import json
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.conf import Config

class OpenAPIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if request.url.path == Config.openapi_prefix.value + "/openapi.json":
            body = b''
            async for chunk in response.body_iterator:
                body += chunk
            schema = json.loads(body.decode('utf-8'))
            base_url = str(request.base_url)
            full_url = base_url.rstrip('/') + Config.openapi_prefix.value
            schema["servers"] = [{"url": full_url}]
            return JSONResponse(schema)
        return response