import httpx

from app.helper.logger import get_logger


async def _log_request(request: httpx.Request):
    """
    Event hook to log request details.
    """
    logger = get_logger()
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"  >> Headers: {request.headers}")
    content_length = request.headers.get('Content-Length')
    if content_length:
        logger.debug(f"  >> Body size: {content_length} bytes")
    else:
        logger.debug("  >> Body: (streaming or empty)")


async def _log_response(response: httpx.Response):
    """
    Event hook to log response details.
    """
    await response.aread()
    logger = get_logger()
    request = response.request
    logger.info(f"Response: {request.method} {request.url} - Status {response.status_code}")
    logger.debug(f"  << Headers: {response.headers}")
    if response.text:
        # Truncate for readability if the body is large
        body_to_log = (response.text[:500] + '...') if len(response.text) > 500 else response.text
        logger.debug(f"  << Body: {body_to_log}")
    else:
        logger.debug("  << Body: (empty)")


def get_http_client_with_logging(base_url: str, timeout: int = 60) -> httpx.AsyncClient:
    """
    Creates an httpx.AsyncClient with detailed request and response logging.
    """
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        event_hooks={
            'request': [_log_request],
            'response': [_log_response]
        }
    )
