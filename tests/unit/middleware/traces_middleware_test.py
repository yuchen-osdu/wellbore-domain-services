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

from opencensus.trace import base_exporter
from fastapi.testclient import TestClient
import pytest
from app.wdms_app import wdms_app, DDMS_V2_PATH
from app.utils import get_or_create_ctx
from tests.unit.test_utils import NopeLogger

from unittest.mock import MagicMock

# Initialize traces exporter in app with a custom one to allow validating our traces
class ExporterInTest(base_exporter.Exporter):
    def __init__(self) -> None:
        self.exported = []

    def export(self, span_datas):
        self.exported += span_datas

    def find(self, correlation_id):
        for sd in self.exported:
            if sd.attributes.get('correlation-id') == correlation_id:
                return sd


@pytest.fixture()
def ctx_fixture():
    """ Create context with a real tracer in it """
    ctx = get_or_create_ctx().set_current_with_value(logger=NopeLogger())
    yield ctx

@pytest.fixture
def client(ctx_fixture):
    yield TestClient(wdms_app)
    wdms_app.dependency_overrides = {}

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
    assert 'correlation-id' in spandata.attributes.keys()
    assert spandata.attributes['correlation-id'] is not None

def test_about_call_traces_existing_correlation_id(client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine    
    response = client.get(build_url("/about"), headers={'correlation-id': 'some correlation id'})
    assert response.status_code == 200
    
    # one call was exported, with correlation-id
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert 'correlation-id' in spandata.attributes.keys()
    assert spandata.attributes['correlation-id'] == 'some correlation id'

def test_about_call_traces_existing_app_id(client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine
    response = client.get(build_url("/about"))
    assert response.status_code == 200

    # one call was exported, without x-app-id
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert 'x-app-id' in spandata.attributes.keys()
    assert spandata.attributes['x-app-id'] is None

    # x-app-id header -> works as well
    client.get(build_url("/about"), headers={'x-app-id': 'some app id'})

    # a second call was exported, with data-partition-id
    assert len(wdms_app.trace_exporter.exported) == 2  # one call => one export
    spandata = wdms_app.trace_exporter.exported[1]
    assert 'x-app-id' in spandata.attributes.keys()
    assert spandata.attributes['x-app-id'] == 'some app id'


def test_about_call_traces_existing_data_partition_id(client: TestClient):

    # Initialize traces exporter in app, like it is in app's startup_event
    wdms_app.trace_exporter = ExporterInTest()

    # no header -> works fine    
    response = client.get(build_url("/about"))
    assert response.status_code == 200
    
    # one call was exported, with data-partition-id
    assert len(wdms_app.trace_exporter.exported) == 1  # one call => one export
    spandata = wdms_app.trace_exporter.exported[0]
    assert 'data-partition-id' in spandata.attributes.keys()
    assert spandata.attributes['data-partition-id'] is None

    # data-partition-id header -> works as well
    client.get(build_url("/about"), headers={'data-partition-id': 'some partition id'})

    # a second call was exported, with data-partition-id
    assert len(wdms_app.trace_exporter.exported) == 2  # one call => one export
    spandata = wdms_app.trace_exporter.exported[1]
    assert 'data-partition-id' in spandata.attributes.keys()
    assert spandata.attributes['data-partition-id'] == 'some partition id'

