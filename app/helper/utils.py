from structlog.contextvars import bind_contextvars
from fastapi import Request
import http


_maximum_azure_attribute_length = 2048
_too_long_url_suffix = '...'


def truncate_long_url(url):
    """ Reduce too long url string to prevent errors when sending to some exporter backends """

    if url and len(url) >= _maximum_azure_attribute_length:
        truncated_url = url[:_maximum_azure_attribute_length - len(_too_long_url_suffix)]
        return f'{truncated_url}{_too_long_url_suffix}'

    return url


def add_fields(**kwargs):
    """
    Add key-value pairs to our homemade logger
    e.g.
        >>> bind_contextvars(a=1, b=2)
        >>> # Then use loggers as per normal
        >>> log.msg("hello")
        a=1 b=2 event='hello'
    Full documentation: https://www.structlog.org/en/stable/contextvars.html
    """
    bind_contextvars(**kwargs)


def _get_status_phrase(status_code):
    try:
        return http.HTTPStatus(status_code).phrase
    except ValueError:
        return str()


STATUS_PHRASES = {
    status_code: _get_status_phrase(status_code) for status_code in range(100, 600)
}


def process_message(request: Request, status_code: int):
    """
        Returns pretty print string to be logger, from Starlette request and status code.
        E.g. Request from: 127.0.0.1:55353 - "GET /api/os-wellbore-ddms/ddms/v2/about" 200 OK
    """
    reason = STATUS_PHRASES[status_code]
    return f'Request from: {_get_client_str(request.client)} - "{request.method}' \
           f' {request.url.path}" {status_code} {reason}'


def _get_client_str(client) -> str:
    """
        Returns a string container host:port from given starlette client
    """
    host, port = client.host, client.port
    if not host:
        return ""
    return f'{host}:{port}'
