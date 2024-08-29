# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import traceback
import sys
import rapidjson

import structlog
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from structlog.contextvars import merge_contextvars

from app.context import get_or_create_ctx


_LOGGER = None


def get_logger():
    return _LOGGER


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
            # Enable display of this error in 'Error reporting' in Google Cloud
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
        """
        Retrieve context created in basic middleware from request info to append them
        in log message as custom attributes
        """
        ctx = get_or_create_ctx()

        if correlation_id := ctx.correlation_id:
            properties.setdefault('correlation-id', correlation_id)

        if ctx.request_id:
            properties.setdefault('request-id', ctx.request_id)

        if ctx.partition_id:
            properties.setdefault('data-partition-id', ctx.partition_id)

        if ctx.app_key:
            properties.setdefault('app-key', ctx.app_key)

        if ctx.api_key:
            properties.setdefault('api-key', ctx.api_key)

    def process(self, msg, kwargs):
        """ Add custom properties to logger message to be sent to AzureAppInsights """
        custom_properties = dict()
        self._set_extra_attrs(custom_properties)
        if custom_properties:
            kwargs['extra'] = dict(custom_dimensions=custom_properties)

        return msg, kwargs


def init_logger(*, service_name, config):
    global _LOGGER

    if config.cloud_provider.value == 'az':
        _LOGGER = create_azure_logger(
            service_name=service_name,
            az_ai_instrumentation_key=config.get('az_ai_instrumentation_key'),
            az_logger_level=config.get('az_logger_level')
        )
    elif config.cloud_provider.value == 'gc':
        _LOGGER = create_gc_logger(
            service_name=service_name,
            gc_log_level=config.get('gc_log_level') 
        )
    elif config.cloud_provider.value == 'baremetal':
        ref_log_level = config.get('ref_log_level')
        log_level = logging.getLevelName(ref_log_level)
        logging.basicConfig(format='%(levelname)s:%(message)s', level=log_level)
        _LOGGER = logging.getLogger(__name__)
    else:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
        _LOGGER = logging.getLogger(__name__)

    return _LOGGER


def create_azure_logger(*, service_name, az_ai_instrumentation_key, az_logger_level):
    """
    Create logger with two handlers:
     - AzureLogHandler: to see Dependencies, Requests, Traces and Exception into Azure monitoring
     - [default] StreamHandler (c.f. logging.basicConfig() ) to see all logs into the std.out captured in container logs

     returns logger configured wrapped into ContextLoggerAdapter
    """
    from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter

    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    if az_ai_instrumentation_key:
        exporter = AzureMonitorLogExporter(connection_string=f'InstrumentationKey={az_ai_instrumentation_key}')
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    az_handler = LoggingHandler()
    if az_logger_level:
        az_handler.setLevel(logging.getLevelName(az_logger_level))

    # stdout handler for direct logging output to stdout.
    stdout_handler = logging.StreamHandler(sys.stdout)

    # Acquire the logger for azure library
    _set_logger_handlers(logger_name='azure', log_level=logging.WARNING, handlers=[stdout_handler, az_handler])

    # Acquire the logger for osdu-core-lib-python-azure
    _set_logger_handlers(logger_name='osdu_az', log_level=logging.INFO, handlers=[stdout_handler, az_handler])

    # Ensure logging messages from Dask (killing, restart worker) are exported to Azure
    _set_logger_handlers(logger_name='distributed.nanny', log_level=logging.WARNING, handlers=[az_handler])

    # Limit logging messages from Dask worker to error and above to prevent exposing secrets in args
    _set_logger_handlers(logger_name='distributed.worker', log_level=logging.ERROR, handlers=[az_handler])

    # Acquire the logger for wdms
    logger = _set_logger_handlers(logger_name=__name__, log_level=logging.DEBUG, handlers=[stdout_handler, az_handler])

    # return wdms logger with Context adapter
    return AzureContextLoggerAdapter(logger, extra=dict())


def create_gc_logger(service_name, gc_log_level):
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
    ch.setLevel(logging.getLevelName(gc_log_level))
    ch.setFormatter(logging.Formatter('%(message)s'))
    my_logger.addHandler(ch)

    std_ddms_app = logging.getLogger(__name__)
    # avoid double logging by the root logger
    std_ddms_app.propagate = False

    return my_logger


def _set_logger_handlers(logger_name, log_level, handlers: list):
    """ Retrieve logger by its name and add handlers to it """
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    for handler in handlers:
        if handler:
            logger.addHandler(handler)

    return logger
