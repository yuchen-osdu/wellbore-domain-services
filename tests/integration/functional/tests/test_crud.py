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

import os
import pytest
from .fixtures import with_wdms_env
from wdms_client.request_builders import build_request
from munch import Munch

kind_list = ['log']
new_parameters_env = {'authorityKind': 'slb',
                      'prefix_data_entity_name': 'wdms_e2e_slb_authority'}

param_kind_depend_on_create = [
    pytest.param(k, marks=pytest.mark.dependency(depends=[f'test_create_record_{k}'])) for k in kind_list
]

#it will only be run once
@pytest.fixture(scope='module')
def get_env_variables_with_authority_in_kind(with_wdms_env):
    env_with_authority_in_kind = with_wdms_env.copy()
    for name, value in new_parameters_env.items():
        env_with_authority_in_kind.set(name, value)
    return env_with_authority_in_kind

@pytest.fixture(params=['data_partition', 'authority_slb'])
def get_env(with_wdms_env, get_env_variables_with_authority_in_kind, request):
    return with_wdms_env if request.param == "data_partition" else get_env_variables_with_authority_in_kind


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize(
    'kind', [pytest.param(k, marks=pytest.mark.dependency(name=f'test_create_record_{k}')) for k in kind_list])
def test_crud_create_record(get_env, kind):
    result = build_request(f'crud.{kind}.create_{kind}').call(get_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    assert len(resobj.recordIdVersions) == 1
    get_env.set(f'{kind}_record_id', resobj.recordIds[0])  # stored the record id for the following tests


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_get_record(get_env, kind):
    result = build_request(f'crud.{kind}.get_{kind}').call(get_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.data.name == f'{get_env.get("prefix_data_entity_name")}_{kind}'


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_record_versions(get_env, kind):
    # get all version of the record
    result = build_request(f'crud.{kind}.get_versions_of_{kind}').call(get_env)
    result.assert_ok()
    resobj = result.get_response_obj()

    record_id = get_env.get(f'{kind}_record_id')
    assert resobj.recordId == record_id
    assert len(resobj.versions) >= 1

    # get specific version of the record
    result = build_request(f'crud.{kind}.get_{kind}_specific_version').call(
        get_env,
        **{f'{kind}_record_version': resobj.versions[0]}  # set/pass version to fetch
    )

    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.data.name == f'{get_env.get("prefix_data_entity_name")}_{kind}'


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_delete_record(get_env, kind):
    result = build_request(f'crud.{kind}.delete_{kind}').call(get_env)
    result.assert_status_code(204)


@pytest.mark.skipif(os.getenv('CLOUD_PROVIDER') == 'local', reason="No schema service in local env")
@pytest.mark.tag('basic', 'crud', 'smoke')
def test_schema_service_correctly_initialized(get_env):
    result = build_request("crud.unknown_kind_osdu_welllog.create_osdu_welllog").call(get_env)
    result.assert_status_code(404)
    error_response = result.get_response_obj()

    print(f"error_response: {error_response}")

    assert error_response.get("origin") == "osdu-data-ecosystem-schema", "Ensure error comes from Schema Service"
    assert len(error_response.get('errors', [])) > 0, "Check field is not empty"
    assert type(error_response.get('errors')[0]) is Munch, "Ensure error is a Munch object"
    assert "Schema is not present" in error_response.get('errors')[0].get('error', {}).get('message')

