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

from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry import trace

from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def get_tracer():
    return trace.get_tracer(__name__)


def _create_azure_exporter(key):
    return AzureMonitorTraceExporter(connection_string=f'InstrumentationKey={key}')


def _create_gc_exporter():
    return CloudTraceSpanExporter()


def initialize_tracer(*, service_name: str, config):
    """
    Create exporters to sent tracing to different tracing platforms e.g. Stackdriver (Google), Azure, etc
    c.f. documentation https://opentelemetry.io/docs/languages/python/exporters/
    """
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })
    provider = TracerProvider(resource=resource)
    exporter = None

    if config.cloud_provider.value == 'gc':
        print("Registering OpenTelemetry CloudTraceSpanExporter")
        exporter = _create_gc_exporter()
    elif config.cloud_provider.value == 'az':
        print("Registering OpenCensus zureMonitorTraceExporter")

        key = config.get('az_ai_instrumentation_key')
        try:
            if type(key) is not None:
                exporter = _create_azure_exporter(key)
        except ValueError as e:
            print('Unable to create AzureExporter:', str(e))
    else:
        print("No trace will be exported")

    if exporter is not None:
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)
    return provider
