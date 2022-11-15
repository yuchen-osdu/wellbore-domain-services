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
from app.wdms_app import wdms_app, DDMS_V2_PATH
from app.auth.auth import require_opendes_authorized_user
from app.helper import traces
from app.conf import Config
from tests.unit.test_utils import ctx_fixture

# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')

# parametrized for backward compatibility with /ddms/v2 APIs
PathPrefixParams = [DDMS_V2_PATH, '']

@pytest.fixture
def client(ctx_fixture, nope_logger_fixture, app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_opendes_authorized_user=False)
    return client



def build_url(prefix: str, path: str):
    return prefix + path

@pytest.mark.parametrize("path_prefix", PathPrefixParams)
@pytest.mark.anyio
async def test_about_contains_build_n_version(client, path_prefix):
    response = await client.get(build_url(path_prefix, "/about"))
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['buildNumber']
    assert response_json['version']


@pytest.mark.skip("global app.conf.Config corruption")
@pytest.mark.parametrize("path_prefix", PathPrefixParams)
@pytest.mark.anyio
async def test_about_with_cloud_provider(client, path_prefix):
    Config.cloud_provider.value = 'my_cloud_provider'
    response = await client.get(build_url(path_prefix, "/about"))
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['cloudEnvironment'] == 'my_cloud_provider'


@pytest.mark.parametrize("path_prefix", PathPrefixParams)
@pytest.mark.anyio
async def test_version_requires_authentication(client, path_prefix):
    response = await client.get(build_url(path_prefix, "/version"))
    assert response.status_code == 403


@pytest.mark.skip("global app.conf.Config corruption")
@pytest.mark.parametrize("path_prefix", PathPrefixParams)
@pytest.mark.anyio
async def test_version_properly_read_details(client_with_authenticated_user, path_prefix):

    # override value of build details
    Config.build_details.value = 'key1=value1; key2=value2'

    response = await client_with_authenticated_user.get(build_url(path_prefix, "/version"))
    assert response.status_code == 200
    response_json = response.json()
    assert response_json['details']['key1'] == 'value1'
    assert response_json['details']['key2'] == 'value2'
