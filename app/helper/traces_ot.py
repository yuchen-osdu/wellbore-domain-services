# Copyright 2024 Schlumberger
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

import os

from opentelemetry import trace

from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OTLP_TRACES_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"


def get_tracer():
    return trace.get_tracer(__name__)


def _create_azure_exporter(connection_str):
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

    return AzureMonitorTraceExporter(connection_string=connection_str)


def _create_gc_exporter():
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

    return CloudTraceSpanExporter()


def _create_aws_exporter(endpoint):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(endpoint=endpoint)


def initialize_tracer(*, service_name: str, config):
    """
    Create exporters to sent tracing to different tracing platforms e.g. Stackdriver (Google), Azure, etc
    c.f. documentation https://opentelemetry.io/docs/languages/python/exporters/
    """
    if config.cloud_provider.value == 'aws':
        # Let the OTEL env detector populate service.name from OTEL_SERVICE_NAME /
        # OTEL_RESOURCE_ATTRIBUTES; an explicit service.name would override them.
        resource = Resource.create()
    else:
        resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = None

    if config.cloud_provider.value == 'gc':
        print("Registering OpenTelemetry CloudTraceSpanExporter")
        exporter = _create_gc_exporter()
    elif config.cloud_provider.value == 'az':
        print("Registering OpenTelemetry AzureMonitorTraceExporter")

        connection_str = config.get('az_ai_connection_str')
        try:
            if type(connection_str) is not None:
                exporter = _create_azure_exporter(connection_str)
        except ValueError as e:
            print('Unable to create AzureExporter:', str(e))
    elif config.cloud_provider.value == 'aws':
        otlp_endpoint = os.environ.get(OTLP_TRACES_ENDPOINT_ENV)
        if otlp_endpoint:
            print("Registering OpenTelemetry OTLPSpanExporter, endpoint:", otlp_endpoint)
            exporter = _create_aws_exporter(otlp_endpoint)
        else:
            print(f"{OTLP_TRACES_ENDPOINT_ENV} not set, no trace will be exported")
    else:
        print("No trace will be exported")

    if exporter is not None:
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)
    return provider
