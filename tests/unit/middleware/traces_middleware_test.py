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
import re

from opencensus.trace import base_exporter
import pytest
from app.wdms_app import DDMS_V2_PATH
from app.routers import probes

from ..test_utils import gen_all_routes_request


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


def build_url(path: str):
    return DDMS_V2_PATH + path


@pytest.mark.anyio
async def test_about_call_creates_correlation_id_if_absent(app_configurable_with_testclient):
    app, client_after_startup = app_configurable_with_testclient(
        trace_exporter=ExporterInTest(),
        fake_opendes_authorized_user=False
    )

    # no header -> works fine
    response = await client_after_startup.get(build_url("/about"))
    assert response.status_code == 200

    # one call was exported, with correlation-id
    assert len(app.trace_exporter.exported) == 1  # one call => one export
    spandata = app.trace_exporter.exported[0]
    assert "correlation-id" in spandata.attributes.keys()
    assert spandata.attributes["correlation-id"] is not None


@pytest.mark.anyio
async def test_about_call_traces_existing_correlation_id(app_configurable_with_testclient):
    app, client_after_startup = app_configurable_with_testclient(
        trace_exporter=ExporterInTest(),
        fake_opendes_authorized_user=False
    )

    # no header -> works fine
    response = await client_after_startup.get(
        build_url("/about"), headers={"correlation-id": "some correlation id"}
    )
    assert response.status_code == 200

    # one call was exported, with correlation-id
    assert len(app.trace_exporter.exported) == 1  # one call => one export
    spandata = app.trace_exporter.exported[0]
    assert "correlation-id" in spandata.attributes.keys()
    assert spandata.attributes["correlation-id"] == "some correlation id"


@pytest.mark.anyio
@pytest.mark.parametrize("header_name", ["x-app-id", "data-partition-id"])
async def test_about_call_traces_request_header(app_configurable_with_testclient, header_name):
    app, client_after_startup = app_configurable_with_testclient(
        trace_exporter=ExporterInTest(),
        fake_opendes_authorized_user=False
    )

    # no header -> works fine
    response = await client_after_startup.get(build_url("/about"))
    assert response.status_code == 200

    # one call was exported, without header
    assert len(app.trace_exporter.exported) == 1  # one call => one export
    spandata = app.trace_exporter.exported[0]
    assert header_name in spandata.attributes.keys()
    assert spandata.attributes[header_name] is None

    # with header -> works as well
    await client_after_startup.get(build_url("/about"), headers={header_name: "some value"})
    assert response.status_code == 200

    # a second call was exported, with header
    assert len(app.trace_exporter.exported) == 2  # one call => one export
    spandata = app.trace_exporter.exported[1]
    assert header_name in spandata.attributes.keys()
    assert spandata.attributes[header_name] == "some value"


@pytest.mark.anyio
@pytest.mark.parametrize("well_record_data_fixture", ["well_v3_record_list", "well_v3_110_record_list"])
@pytest.mark.slow
async def test_call_trace_url(app_configurable_with_testclient, mock_storage_client_holding_data, well_v2_record_list,
                        well_record_data_fixture, request):
    well_record_data = request.getfixturevalue(well_record_data_fixture)
    # empty storage client mock required because we use get_record result in route.
    storage_client_mock = mock_storage_client_holding_data(data=[])

    app, client_after_startup = app_configurable_with_testclient(
        storage_client_mock=storage_client_mock,
        trace_exporter=ExporterInTest(),
        fake_opendes_authorized_user=False
    )

    path_var_rgx = re.compile(r"/{[\w:]*}")

    # special id case
    well_v2_var_rgx = re.compile(r"/v2/wells/{wellid[:\w]?}")
    well_v3_var_rgx = re.compile(r"/v3/wells/{wellid[:\w]?}")

    def path_sub(path):
        path_with_id = path
        # modify on regex match, or noop

        # special id case -> pick one id from example data
        path_with_id = re.sub(well_v2_var_rgx, f"/v2/wells/{well_v2_record_list[0].id}", path_with_id)
        path_with_id = re.sub(well_v3_var_rgx, f"/v3/wells/{well_record_data[0].id}", path_with_id)

        # other cases...
        path_with_id = re.sub(path_var_rgx, r"/123456", path_with_id)

        return path_with_id

    call_count = 0

    # startup event has been called (client has been called in a context), so all routers should be mounted
    for method, path in gen_all_routes_request(app):

        # skip routes created on app instantiation
        # which are known to not have a trace
        if path in [
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ] + [r.path for r in probes.router.routes]:  # we also need to exclude probes routes as they are not traced
            continue

        path_with_id = path_sub(path)
        call_count += 1

        # Note : most of these will fail because of authentication -> we do not need to mock complex behaviour
        resp = await client_after_startup.request(method=method, url=path_with_id)
        print(f"{path_with_id} -> {resp.status_code}")

        # one call was exported
        assert (
            len(app.trace_exporter.exported) == call_count
        )  # one call => one export
        spandata = app.trace_exporter.exported[call_count - 1]

        # with expected name and route
        assert spandata.name == path_with_id
        assert spandata.attributes["http.route"] == path_with_id
