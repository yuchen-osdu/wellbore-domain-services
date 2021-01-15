import logging
import traceback
import sys

from app.conf import Config
from app.utils import get_or_create_ctx

import structlog
from structlog.contextvars import merge_contextvars, bind_contextvars
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
import rapidjson

_LOGGER = None


def get_logger():
    return _LOGGER


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


class StackDriverRenderer(object):
    def __init__(self, service_name=None):
        self.service_name = service_name

    def __call__(self, _, method, event_dict):
        if self.service_name:
            event_dict['serviceContext'] = {'service': self.service_name}

        # rename event to msg
        if 'event' in event_dict:
            event_dict['message'] = event_dict['event']
            del event_dict['event']

        # Required by stackdriver to display level of error accordingly
        event_dict.setdefault("severity", method)

        if method == 'error' or method == 'critical':
            # Enable display of this error in 'Error reporting' in GCP
            event_dict['@type'] = 'type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent'
            if sys.exc_info()[0]:
                # check if an exception exist https://docs.python.org/2/library/sys.html#sys.exc_info
                event_dict['stack_trace'] = traceback.format_exc()

        return event_dict


class AzureContextLoggerAdapter(logging.LoggerAdapter):
    """
    This adapter adds contextual information into messages to be logged in Azure monitoring.
    It aims to add as custom properties contextual fields, following this instructions:
    https://docs.microsoft.com/en-us/azure/azure-monitor/app/opencensus-python
    """

    @staticmethod
    def _set_extra_attrs(properties):
        ctx = get_or_create_ctx()

        properties.setdefault('correlation-id', ctx.correlation_id)
        properties.setdefault('request-id', ctx.request_id)
        properties.setdefault('data-partition-id', ctx.partition_id)
        properties.setdefault('app-key', ctx.app_key)
        properties.setdefault('api-key', ctx.api_key)

    def process(self, msg, kwargs):
        """
        Retrieve context created in basic middleware from request info to append them
        in log message as custom attributes
        """
        custom_properties = dict()
        self._set_extra_attrs(custom_properties)
        kwargs['extra'] = dict(custom_dimensions=custom_properties)

        return msg, kwargs


def init_logger():
    global _LOGGER

    if Config.cloud_provider.value == 'az':
        _LOGGER = create_azure_logger()
    elif Config.cloud_provider.value == 'gcp':
        _LOGGER = create_gcp_logger()
    else:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
        _LOGGER = logging.getLogger(__name__)

    return _LOGGER


def create_azure_logger():
    """
    Create logger with two handlers:
     - AzureLogHandler: to see Dependencies, Requests, Traces and Exception into Azure monitoring
     - [default] StreamHandler (c.f. logging.basicConfig() ) to see all logs into the std.out captured in container logs

     returns logger configured wrapped into ContextLoggerAdapter
    """
    config_integration.trace_integrations(['logging'])
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    logger.addHandler(ch)

    key = Config.get('az_ai_instrumentation_key')
    logger_level = Config.get('az_logger_level')
    handler = AzureLogHandler(connection_string=f'InstrumentationKey={key}')
    handler.setLevel(logging.getLevelName(logger_level))
    logger.addHandler(handler)

    return AzureContextLoggerAdapter(logger, extra=dict())


def create_gcp_logger(service_name='wellbore-ddms'):
    """
    Initialize structlog with following configuration:
        - Make logs compatible with Stackdriver
        - if dev_mode, display stacktrace out of json item
    Returns structlog
    """

    structlog.configure(
        processors=[
            StackDriverRenderer(service_name=service_name),
            merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializer=rapidjson.dumps)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    my_logger = structlog.getLogger(__name__)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter('%(message)s'))
    my_logger.addHandler(ch)

    std_ddms_app = logging.getLogger(__name__)
    # avoid double logging by the root logger
    std_ddms_app.propagate = False

    return my_logger
