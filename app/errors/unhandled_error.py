from fastapi.logger import logger
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


async def unhandled_error_handler(req: Request, exc: Exception) -> JSONResponse:
    """
    To handle wild exception not caught by other exception handlers
    """
    logger.error(f"{req.url} - {exc}")
    return JSONResponse({"errors": [exc.args]}, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
