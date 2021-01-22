from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from app.helper.logger import get_logger


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    To handle wild exception not caught by other exception handlers
    """
    get_logger().exception(f"unhandled_error_handler - {request.url}")

    return JSONResponse({"error": [str(exc)]}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
