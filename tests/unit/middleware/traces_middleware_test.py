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

import pytest
from unittest import mock
from fastapi import FastAPI
from starlette.testclient import TestClient

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SimpleSpanProcessor

from app.helper import logger
from app.model.osdu_record_id import WellLogId
from app.middleware import TracingMiddlewareOT, CreateBasicContextMiddleware


class ExporterInTest(SpanExporter):
    """ Initialize traces exporter in app with a custom one to allow validating our traces """
    def __init__(self) -> None:
        self.exported = []

    def export(self, spans: list):
        self.exported += spans

    def shutdown(self) -> None:
        pass

    def find(self, correlation_id):
        for sd in self.exported:
            if sd.attributes.get("correlation-id") == correlation_id:
                return sd


@pytest.fixture(scope="function")
async def create_app_with_routes_middleware():
    logger._LOGGER = mock.Mock()
    app = FastAPI()
    app.add_middleware(TracingMiddlewareOT, skip_for_path_suffix=[])
    app.add_middleware(CreateBasicContextMiddleware, config=mock.Mock(), injector=mock.Mock())

    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

    exporter = ExporterInTest()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    yield app, exporter

    # exporter is static, reset it after each test
    exporter.exported = []


@pytest.mark.anyio
async def test_correlation_auto_set_if_missing(create_app_with_routes_middleware):
    app, exporter = create_app_with_routes_middleware
    client = TestClient(app)

    @app.get("/bob-route-test")
    def route():
        return "Hello world"

    client.get("/bob-route-test")

    assert len(exporter.exported) == 1
    assert "correlation-id" in exporter.exported[0].attributes
    assert len(exporter.exported[0].attributes["correlation-id"]) == 36  # an uuid is 36 characters long

    del client


@pytest.mark.anyio
async def test_traces_attributes(create_app_with_routes_middleware):
    app, exporter = create_app_with_routes_middleware

    @app.get("/records/{welllogid}")
    def route(welllogid: WellLogId):
        return "this is a WellLog"

    client = TestClient(app)

    headers_name = ["correlation-id", "x-app-id", "data-partition-id", 'x-user-id']
    headers = {}
    for h in headers_name:
        headers[h] = f"my-{h}"

    response = client.get("/records/osdu:work-product-component--WellLog:12345:1", headers=headers)
    assert response.status_code == 200, response.text

    assert len(exporter.exported)
    all_trace_attributes = exporter.exported[0].attributes

    # ensure headers has been set to trace attributes
    assert all_trace_attributes["correlation-id"] == "my-correlation-id"
    assert all_trace_attributes["x-app-id"] == "my-x-app-id"
    assert all_trace_attributes["data-partition-id"] == "my-data-partition-id"
    assert all_trace_attributes['user-id'] == 'my-x-user-id'

    # ensure all default http attributes are set.
    assert all_trace_attributes['http.host'] == 'testserver'
    assert all_trace_attributes['http.method'] == 'GET'
    assert all_trace_attributes['http.url'] == "http://testserver/records/osdu:work-product-component--WellLog:12345:1"
    assert all_trace_attributes['http.route'] == "/records/{welllogid}"
    assert all_trace_attributes['http.status_code'] == 200
    assert all_trace_attributes['response.header Content-type'] == 'application/json'
    assert all_trace_attributes['response.header Content-length'] == '19'

    del client
