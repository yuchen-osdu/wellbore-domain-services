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
from functools import wraps
from asyncio import iscoroutinefunction
from typing import Callable

from fastapi.routing import APIRoute
from opencensus.common.transports.async_ import AsyncTransport
from opencensus.trace import base_exporter, execution_context
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator
from opencensus.trace.span import SpanKind
from starlette.requests import Request
from starlette.responses import Response

from app.conf import Config
from .utils import rename_cloud_role_func, azure_traces_processing, COMPONENT


"""
How to add specific span in a method

>> from app.context import Context, get_ctx
>>
>> @router.get("/about", response_model=MyResponseClass)
>> async def my_endpoint_method(ctx: Context = Depends(get_ctx)) -> MyResponseClass:
>>     
>>         with ctx.tracer.span(name='test-sub-about.construct'):
>>             result = someComputation()
>>         with ctx.tracer.span(name='test-sub-about.construct'):
>>             return MyResponseClass(result)

"""


class TracingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        path = self.path

        async def custom_route_handler(request: Request) -> Response:
            # https://www.starlette.io/requests/#other-state
            request.state.traced_route = path
            response: Response = await original_route_handler(request)
            return response

        return custom_route_handler


def get_trace_propagator() -> TraceContextPropagator:
    """
        Returns the implementation of standard tracing propagation as defined
        by W3C: https://www.w3.org/TR/trace-context/
    """
    return TraceContextPropagator()


def _create_azure_exporter(key: str):
    from opencensus.ext.azure.trace_exporter import AzureExporter
    return AzureExporter(connection_string=f'InstrumentationKey={key}')


def _create_gcp_exporter():
    from opencensus.ext.stackdriver.trace_exporter import StackdriverExporter
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
            az_exporter.add_telemetry_processor(rename_cloud_role_func(service_name))
            az_exporter.add_telemetry_processor(azure_traces_processing)
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


def with_trace(label: str, span_kind=SpanKind.CLIENT):
    """ decorate the function adding trace """
    def decorate(target):

        if iscoroutinefunction(target):

            @wraps(target)
            async def async_inner(*args, **kwargs):
                tracer = execution_context.get_opencensus_tracer()
                if tracer is None:
                    return await target(*args, **kwargs)

                with tracer.span(name=label) as span:
                    span.span_kind = span_kind
                    return await target(*args, **kwargs)

            return async_inner

        @wraps(target)
        def sync_inner(*args, **kwargs):
            tracer = execution_context.get_opencensus_tracer()
            if tracer is None:
                return target(*args, **kwargs)

            with tracer.span(name=label) as span:
                span.span_kind = span_kind
                return target(*args, **kwargs)

        return sync_inner

    return decorate
