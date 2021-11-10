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

import os
import pytest
import rapidjson as json
from tests.unit.test_utils import ctx_fixture
from fastapi.testclient import TestClient
from openapi_spec_validator import validate_spec

from app.helper import traces
from app.utils import format_routes
from app.wdms_app import wdms_app
import app.conf as conf

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

# Initialize routes
environment_dict = os.environ.copy()
conf.Config = conf.ConfigurationContainer.with_load_all(
    environment_dict=environment_dict,
    contextual_loader=None
)
prefix = conf.Config.get('openapi_filter_prefix')
tags = conf.Config.get('openapi_filter_tags')
if tags:
    tags = tags.split(',')
format_routes(wdms_app, prefix, tags)


@pytest.fixture
def client(ctx_fixture):
    yield TestClient(wdms_app)
    wdms_app.dependency_overrides = {}


@pytest.fixture
def openapi_json(client):
    # get the openapi spec
    response = client.get("/openapi.json")
    assert response.status_code == 200
    yield response.json()


def test_api_spec(openapi_json):
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


def test_api_spec_for_duplicates(openapi_json):
    # Check operationId for all paths are different
    # structure is
    # root
    #   + paths
    #       + url for instance "/alpha/ddms/v2/logs/{record_id}/data"
    #           + method for instance get, post, ...
    #               + operationId
    path_dict = openapi_json.get("paths", None)
    operation_id_set = set()
    assert path_dict is not None
    for url, url_dict in path_dict.items():
        for method, method_dict in url_dict.items():
            operation_id = method_dict.get("operationId", None)
            assert operation_id not in operation_id_set, f"{method}:{url} {operation_id} already defined"
            operation_id_set.add(operation_id)


def test_open_api_validity(openapi_json):
    validate_spec(openapi_json)
