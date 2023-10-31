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
import json

import pytest

from .fixtures import with_wdms_env
from wdms_client.request_builders import build_request, diff_record_against_ref

kind_list = [
    'osdu_wellbore_100',
    'osdu_wellbore_111',
    'osdu_wellbore_120',
    'osdu_wellbore',# is the latest
    'osdu_well_100',
    'osdu_well_110',
    'osdu_well',# is the latest
    'osdu_welllog',
    'osdu_wellboretrajectory',
    'osdu_wellboremarkerset',
    'osdu_wellboreintervalset_100'
]

# parametrize of kind + dependency on the create_record
param_kind_depend_on_create = [
    pytest.param(k, marks=pytest.mark.dependency(depends=[f'test_create_record_{k}'])) for k in kind_list
]


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize(
    'kind', [pytest.param(k, marks=pytest.mark.dependency(name=f'test_create_record_{k}')) for k in kind_list])
def test_create_record(with_wdms_env, kind):
    result = build_request(f'crud.{kind}.create_{kind}').call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    assert len(resobj.recordIdVersions) == 1
    with_wdms_env.set(f'{kind}_record_id', resobj.recordIds[0])  # stored the record id for the following tests


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_get_record(with_wdms_env, kind):
    result = build_request(f'crud.{kind}.get_{kind}').call(with_wdms_env)
    result.assert_ok()
    res_dict = result.get_response_obj().toDict()
    diff = diff_record_against_ref(kind, res_dict)
    assert not diff



@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_record_versions(with_wdms_env, kind):
    # get all version of the record
    result = build_request(f'crud.{kind}.get_versions_of_{kind}').call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()

    record_id = with_wdms_env.get(f'{kind}_record_id')
    assert resobj.recordId == record_id
    assert len(resobj.versions) >= 1

    # get specific version of the record
    result = build_request(f'crud.{kind}.get_{kind}_specific_version').call(
        with_wdms_env,
        **{f'{kind}_record_version': resobj.versions[len(resobj.versions) - 1]}  # set/pass version to fetch
    )

    result.assert_ok()


@pytest.mark.tag('basic', 'crud', 'smoke')
@pytest.mark.parametrize('kind', param_kind_depend_on_create)
def test_crud_delete_record(with_wdms_env, kind):
    result = build_request(f'crud.{kind}.delete_{kind}').call(with_wdms_env)
    result.assert_status_code(204)


GETAS_PARAMS = [
    'wellbore',
    'well'
]


@pytest.fixture()
def delfi_id(with_wdms_env, kind):
    # Create a delfi well
    result = build_request(f"crud.{kind}.create_{kind}").call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    delfi_record_id = resobj.recordIds[0]
    with_wdms_env.set(f'{kind}_record_id', delfi_record_id)

    yield delfi_record_id

    # Cleanup
    result = build_request(f"crud.{kind}.delete_{kind}").call(with_wdms_env)
    result.assert_ok()


@pytest.mark.tag('crud', 'smoke')
@pytest.mark.parametrize('kind', GETAS_PARAMS)
def test_crud_get_as_record(delfi_id, kind, with_wdms_env):
    delfi_record_id = delfi_id
    with_wdms_env.set(f'osdu_{kind}_record_id', delfi_record_id)

    # Get it as osdu wellbore with delfi id
    result = build_request(f'crud.osdu_{kind}.get_osdu_{kind}').call(with_wdms_env)
    result.assert_status_code(422)
