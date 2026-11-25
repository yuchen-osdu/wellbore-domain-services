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
from app.wdms_app import wdms_app
from app.auth.auth import require_opendes_authorized_user
from app.conf import Config
from tests.unit.test_utils import ctx_fixture



@pytest.fixture
def client(ctx_fixture, nope_logger_fixture, app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(fake_opendes_authorized_user=False)
    return client


@pytest.fixture
def client_with_authenticated_user(ctx_fixture, nope_logger_fixture, app_configurable_with_testclient):
    _, client = app_configurable_with_testclient()
    return client


@pytest.mark.anyio
async def test_about_contains_build_n_version(client):
    response = await client.get("/about")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['buildNumber']
    assert response_json['version']


@pytest.mark.skip("global app.conf.Config corruption")
@pytest.mark.anyio
async def test_about_with_cloud_provider(client):
    Config.cloud_provider.value = 'my_cloud_provider'
    response = await client.get("/about")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['cloudEnvironment'] == 'my_cloud_provider'


@pytest.mark.anyio
async def test_version_requires_authentication(client):
    response = await client.get("/version")
    # HTTPBearer returns 401 (not 403) when the Authorization header is missing
    assert response.status_code == 401


@pytest.mark.skip("global app.conf.Config corruption")
@pytest.mark.anyio
async def test_version_properly_read_details(client_with_authenticated_user):

    # override value of build details
    Config.build_details.value = 'key1=value1; key2=value2'

    response = await client_with_authenticated_user.get("/version")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json['details']['key1'] == 'value1'
    assert response_json['details']['key2'] == 'value2'


@pytest.mark.anyio
async def test_version(client_with_authenticated_user):
    response = await client_with_authenticated_user.get("/version")

    assert response.status_code == 200
    response_json = response.json()

    assert 'details' in response_json
    assert 'version' in response_json
    assert 'release' in response_json
    assert response_json['service'] == 'Wellbore DDMS OSDU'
    assert response_json['buildNumber'] == 'local'


@pytest.mark.anyio
async def test_info_does_not_require_authentication(client):
    response = await client.get("/ddms/v3/info")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['groupId'] == 'org.opengroup.osdu'
    assert response_json['artifactId'] == 'os-wellbore-ddms'
    assert response_json['version']
    assert response_json['connectedOuterServices'] == []


@pytest.mark.anyio
async def test_info_reads_build_details(client, monkeypatch):
    # monkeypatch restores the shared Config after the test
    monkeypatch.setattr(Config.build_details, 'value',
                        'build_date="2026-10-28T12:00:00Z";build_number=abc1234;build_origin=Gitlab;'
                        'commit_id=abc1234;commit_branch=master')
    monkeypatch.setattr(Config.commit_message, 'value', 'Fix a; b = c')

    response = await client.get("/ddms/v3/info")
    assert response.status_code == 200

    response_json = response.json()
    assert response_json['buildTime'] == '2026-10-28T12:00:00Z'
    assert response_json['branch'] == 'master'
    assert response_json['commitId'] == 'abc1234'
    assert response_json['commitMessage'] == 'Fix a; b = c'


@pytest.mark.anyio
async def test_info_without_build_details_returns_nulls(client, monkeypatch):
    monkeypatch.setattr(Config.build_details, 'value', '')
    monkeypatch.setattr(Config.commit_message, 'value', '')

    response_json = (await client.get("/ddms/v3/info")).json()
    assert response_json['buildTime'] is None
    assert response_json['branch'] is None
    assert response_json['commitId'] is None
    assert response_json['commitMessage'] is None


@pytest.mark.anyio
async def test_info_alias_matches_versioned_path(client):
    response = await client.get("/v3/info")
    assert response.status_code == 200
    assert response.json() == (await client.get("/ddms/v3/info")).json()
