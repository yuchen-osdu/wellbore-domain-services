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

"""
This test ensures the API spec committed with the sources stays accurate.
If the test fails, it replaces the saved spec with the current version.
The updated spec file must then be committed with the latest changes.
"""

OPENAPI_PATH = 'spec/generated/openapi.json'

from fastapi.testclient import TestClient
import pytest
from app.wdms_app import wdms_app
from app.helper import traces
from tests.unit.test_utils import ctx_fixture

import rapidjson as json

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.fixture
def client(ctx_fixture):
    yield TestClient(wdms_app)
    wdms_app.dependency_overrides = {}

def build_url(path: str):
    return wellbore_api_group_prefix + path

def test_api_spec(client):
    # get the openapi spec
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_json = response.json()
    openapi_text = json.dumps(openapi_json, sort_keys=True, indent=2)
    # get the saved spec
    with open(OPENAPI_PATH, 'r') as specfile:
        specfile_json = json.load(specfile)
        specfile_text = json.dumps(specfile_json, sort_keys=True, indent=2)
    # compare formatted json strings
    if openapi_text != specfile_text:
        # save updated spec
        with open(OPENAPI_PATH, 'w') as specfile:
            specfile.write(openapi_text)
        # assert error
        assert False, f"{OPENAPI_PATH} has changed, commit the updated file"
