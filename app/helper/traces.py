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

from app.conf import Config

from opencensus.common.transports.async_ import AsyncTransport
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace import base_exporter
from opencensus.ext.stackdriver.trace_exporter import StackdriverExporter
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator

from starlette.requests import Request
import http
"""
How to add specific span in a method

>> from app.utils import Context, get_ctx
>>
>> @router.get("/about", response_model=MyResponseClass)
>> async def my_endpoint_method(ctx: Context = Depends(get_ctx)) -> MyResponseClass:
>>     
>>         with ctx.tracer.span(name='test-sub-about.construct'):
>>             result = someComputation()
>>         with ctx.tracer.span(name='test-sub-about.construct'):
>>             return MyResponseClass(result)

"""


def _create_azure_exporter(key: str):
    return AzureExporter(connection_string=f'InstrumentationKey={key}')


def _create_gcp_exporter():
    return StackdriverExporter(transport=AsyncTransport)


def create_exporter(service_name):
    """
    Create exporters to sent tracing to different tracing platforms e.g. Stackdriver (Google) or Azure
    c.f. documentation https://opencensus.io/exporters/supported-exporters/python/
    """
    combined_exporter = CombinedExporter(service_name=service_name)

    if Config.cloud_provider.value == 'gcp':
        print("Registering OpenCensus trace Stackdriver")

        stackdriver_exporter = _create_gcp_exporter()
        combined_exporter.add_exporter(stackdriver_exporter)
    elif Config.cloud_provider.value == 'az':
        print("Registering OpenCensus trace AzureExporter")

        key = Config.get('az_ai_instrumentation_key')
        try:
            az_exporter = _create_azure_exporter(key)
            combined_exporter.add_exporter(az_exporter)
        except ValueError as e:
            print('Unable to create AzureExporter:', str(e))
    else:
        print("No trace will be exported")

    return combined_exporter


class CombinedExporter(base_exporter.Exporter):
    """
        The Opencensus lib allow to have only 1 exporter, so this class is used to combine multiple exporters
    """
    def __init__(self, exporters=None, service_name="undefined"):
        if exporters is None:
            exporters = []
        self.exporters = exporters
        self.service_name = service_name

    def add_exporter(self, exporter):
        self.exporters.append(exporter)

    def export(self, span_datas):
        # Add shared attributes to all spans
        for span_data in span_datas:
            span_data.attributes[COMPONENT] = self.service_name

        for e in self.exporters:
            e.export(span_datas)


def get_trace_propagator() -> TraceContextPropagator:
    """
        Returns the implementation of standard tracing propagation as defined
        by W3C: https://www.w3.org/TR/trace-context/
    """
    return TraceContextPropagator()


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