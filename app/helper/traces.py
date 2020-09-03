import os
from opencensus.common.transports.async_ import AsyncTransport
from opencensus.ext.stackdriver.trace_exporter import StackdriverExporter
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace import base_exporter


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


def create_exporter(service_name):
    """
    Create exporters to sent tracing to different tracing platforms e.g. Stackdriver (Google) or Azure
    c.f. documentation https://opencensus.io/exporters/supported-exporters/python/
    """

    combined_exporter = CombinedExporter(service_name=service_name)

    export_to_stackdriver = os.environ.get("STACKDRIVER_TELEMETRY_EXPORTER_ENABLED")
    if export_to_stackdriver:
        print("Registering OpenCensus Stackdriver traces exporter")

        stackdriver_exporter = StackdriverExporter(transport=AsyncTransport)
        combined_exporter.add_exporter(stackdriver_exporter)
    else:
        print("No trace will be exported, Stackdriver skipped")

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