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
from structlog.contextvars import merge_contextvars
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration

from app.conf import Config
from app.utils import get_or_create_ctx
from app.helper.utils import rename_cloud_role_func

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


def init_logger(service_name):
    global _LOGGER

    if Config.cloud_provider.value == 'az':
        _LOGGER = create_azure_logger(service_name)
    elif Config.cloud_provider.value == 'gcp':
        _LOGGER = create_gcp_logger(service_name)
    else:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
        _LOGGER = logging.getLogger(__name__)

    return _LOGGER


def create_azure_logger(service_name):
    """
    Create logger with two handlers:
     - AzureLogHandler: to see Dependencies, Requests, Traces and Exception into Azure monitoring
     - [default] StreamHandler (c.f. logging.basicConfig() ) to see all logs into the std.out captured in container logs

     returns logger configured wrapped into ContextLoggerAdapter
    """
    config_integration.trace_integrations(['logging'])

    # stdout handler for direct logging output to stdout.
    stdout_handler = logging.StreamHandler(sys.stdout)

    #  AzurelogHandler for logging to azure appinsight
    key = Config.get('az_ai_instrumentation_key')
    logger_level = Config.get('az_logger_level')
    az_handler = AzureLogHandler(connection_string=f'InstrumentationKey={key}')
    az_handler.setLevel(logging.getLevelName(logger_level))
    az_handler.add_telemetry_processor(rename_cloud_role_func(service_name))

    # Acquire the logger for azure library
    az_logger = logging.getLogger('azure')
    az_logger.setLevel(logging.DEBUG)
    az_logger.addHandler(stdout_handler)

    # Acquire the logger for osdu-core-lib-python-azure
    osdu_core_lib_logger = logging.getLogger('osdu_az')
    osdu_core_lib_logger.setLevel(logging.DEBUG)
    osdu_core_lib_logger.addHandler(stdout_handler)
    osdu_core_lib_logger.addHandler(az_handler)

    # Acquire the logger for wdms
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    logger.addHandler(az_handler)

    # return wdms logger with Context adapter
    return AzureContextLoggerAdapter(logger, extra=dict())


def create_gcp_logger(service_name):
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
