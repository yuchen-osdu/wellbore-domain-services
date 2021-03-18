from structlog.contextvars import bind_contextvars
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES

from fastapi import Request
import http


def rename_cloud_role_func(service_name):
    """
        Return a processor function to change 'Cloud Role Name' in AppInsight with given service_name variable.
        It's used by AzureLogHandler and AzureExporter.
        https://docs.microsoft.com/en-us/azure/azure-monitor/app/api-filtering-sampling#opencensus-python-telemetry-processors
    """
    def callback_func(envelope):
        envelope.tags['ai.cloud.role'] = service_name
        return True

    return callback_func


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


"""
Attributes helper have been used similarly to some examples:
Ex of other middleware : https://github.com/census-instrumentation/opencensus-python/blob/master/contrib/opencensus-ext-django/opencensus/ext/django/middleware.py
https://github.com/census-instrumentation/opencensus-python/blob/master/opencensus/trace/attributes_helper.py
"""
HTTP_HOST = COMMON_ATTRIBUTES['HTTP_HOST']
HTTP_METHOD = COMMON_ATTRIBUTES['HTTP_METHOD']
HTTP_PATH = COMMON_ATTRIBUTES['HTTP_PATH']
HTTP_ROUTE = COMMON_ATTRIBUTES['HTTP_ROUTE']
HTTP_URL = COMMON_ATTRIBUTES['HTTP_URL']
HTTP_STATUS_CODE = COMMON_ATTRIBUTES['HTTP_STATUS_CODE']
HTTP_REQUEST_SIZE = COMMON_ATTRIBUTES['HTTP_REQUEST_SIZE']
HTTP_RESPONSE_SIZE = COMMON_ATTRIBUTES['HTTP_RESPONSE_SIZE']
COMPONENT = COMMON_ATTRIBUTES['COMPONENT']
