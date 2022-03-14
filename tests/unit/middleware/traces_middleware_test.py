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
import re
import types
from typing import Optional
from unittest.mock import AsyncMock

from opencensus.trace import base_exporter
from fastapi.testclient import TestClient
import pytest
from starlette.routing import Router, Route, Mount

from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.wdms_app import wdms_app, base_app, DDMS_V2_PATH, app_injector


# Initialize traces exporter in app with a custom one to allow validating our traces
class ExporterInTest(base_exporter.Exporter):
    def emit(self, span_datas):
        pass

    def __init__(self) -> None:
        self.exported = []

    def export(self, span_datas):
        self.exported += span_datas

    def find(self, correlation_id):
        for sd in self.exported:
            if sd.attributes.get("correlation-id") == correlation_id:
                return sd


@pytest.fixture
def client(local_dev_config, nope_logger_fixture):
    with TestClient(wdms_app) as client:
        yield client


@pytest.fixture
def client_after_startup(local_dev_config, nope_logger_fixture):
    import odes_storage

    # using base_app client to trigger startup event.
    with TestClient(base_app):

        # defining a fake_get_record to not break, in case we reach the stage where we need the return
        async def fake_get_record(self, id, data_partition_id):
            return odes_storage.models.Record()

        async def build_mock_storage():
            storage_mock = AsyncMock()
            # fake get_record to not break
            storage_mock.get_record = types.MethodType(fake_get_record, storage_mock)
            return storage_mock

        async def build_mock_search():
            return AsyncMock()

        app_injector.register(StorageRecordServiceClient, build_mock_storage)
        app_injector.register(SearchServiceClient, build_mock_search)

        with TestClient(wdms_app) as client:
            yield client


def build_url(path: str):
    return DDMS_V2_PATH + path


def test_about_call_creates_correlation_id_if_absent(client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine
    response = client.get(build_url("/about"))
    assert response.status_code == 200

    # one call was exported, with correlation-id
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert "correlation-id" in spandata.attributes.keys()
    assert spandata.attributes["correlation-id"] is not None


def test_about_call_traces_existing_correlation_id(client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine
    response = client.get(
        build_url("/about"), headers={"correlation-id": "some correlation id"}
    )
    assert response.status_code == 200

    # one call was exported, with correlation-id
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert "correlation-id" in spandata.attributes.keys()
    assert spandata.attributes["correlation-id"] == "some correlation id"


@pytest.mark.parametrize("header_name", ["x-app-id", "data-partition-id"])
def test_about_call_traces_request_header(header_name, client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine
    response = client.get(build_url("/about"))
    assert response.status_code == 200

    # one call was exported, without header
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert header_name in spandata.attributes.keys()
    assert spandata.attributes[header_name] is None

    # with header -> works as well
    client.get(build_url("/about"), headers={header_name: "some value"})
    assert response.status_code == 200

    # a second call was exported, with header
    assert len(wdms_app.trace_exporter.exported) == 2  # one call => one export
    spandata = wdms_app.trace_exporter.exported[1]
    assert header_name in spandata.attributes.keys()
    assert spandata.attributes[header_name] == "some value"


def gen_all_routes_request(rtr: Router, prefix: Optional[str] = None):
    if prefix is None:
        prefix = ""

    for route in rtr.routes:
        if isinstance(route, Mount):
            # if this is a Mount, we need to recurse on the route
            yield from gen_all_routes_request(route.app, route.path)
        elif isinstance(route, Route):
            for method in route.methods:
                yield method, prefix + route.path
        else:
            RuntimeError(f"{route} routes retrieval not implemented")


def test_call_trace_url(client_after_startup: TestClient):
    # Initialize traces exporter in app, like it is in app's startup_event
    client_after_startup.app.trace_exporter = ExporterInTest()

    path_var_rgx = re.compile(r"/{[\w:]*}")

    call_count = 0

    # startup event has been called (client has been called in a contest), so all routers should be mounted
    for method, path in gen_all_routes_request(client_after_startup.app):

        # skip routes created on app instantiation
        # which are known to not have a trace
        if path in [
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ]:
            continue

        # replace variable in path with fake id...
        fake_path = re.sub(path_var_rgx, r"/123456", path)
        print(fake_path)

        call_count += 1

        client_after_startup.request(method=method, url=fake_path)

        # one call was exported
        assert (
            len(client_after_startup.app.trace_exporter.exported) == call_count
        )  # one call => one export
        spandata = client_after_startup.app.trace_exporter.exported[call_count - 1]

        # with expected name and route
        assert spandata.name == fake_path
        assert spandata.attributes["http.route"] == path
