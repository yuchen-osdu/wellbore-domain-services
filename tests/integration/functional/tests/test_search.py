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
from .fixtures import with_wdms_env
from wdms_client.request_builders.wdms.search_apis.setup import *
from wdms_client.request_builders.wdms.search_apis.search import *
from time import sleep

new_parameters_env = {'authorityKind': 'slb',
                      'prefix_data_entity_name': 'wdms_e2e_slb_authority'}

#it will only be run once
@pytest.fixture(scope='module')
def get_env_variables_with_authority_in_kind(with_wdms_env):
    env_with_authority_in_kind = with_wdms_env.copy()
    for name, value in new_parameters_env.items():
        env_with_authority_in_kind.set(name, value)
    return env_with_authority_in_kind

# to test authority slb in kind, add 'authority_slb' param to the fixture
# params=['data_partition', 'authority_slb']
@pytest.fixture(params=['data_partition'])
def get_env(with_wdms_env, get_env_variables_with_authority_in_kind, request):
    return with_wdms_env if request.param == "data_partition" else get_env_variables_with_authority_in_kind

@pytest.fixture(params=['query', 'fastquery'])
def set_search_query_type(get_env, request):
    env = get_env
    env.set('search_query_type', request.param)

def query_for_record_set_available(env):
    result = build_request_seach_tests_setup_start().call(env)
    result.assert_ok()
    return result.get_response_obj()

@pytest.mark.tag('search')
@pytest.mark.dependency()
def test_setup_for_search(get_env):
    # TODO this must be revisited to have independent setup for each needed record
    wait_attempt = 10

    # set here the version the data set of record needed for the tests
    env = get_env
    env.set('search_record_version', '0001')
    # this value is use in the query to fetch the record

    env.set('search_query_type', 'fastquery')

    query_result = query_for_record_set_available(env)
    nb_record = len(query_result.results)
    #set env if found
    if nb_record == 0:
        # create one wellbore
        record_id = build_request_seach_tests_setup_create_wellbore().call(
            env, assert_status=200).get_response_obj().recordIds[0]
        env.set("setup_search_{{prefix_data_entity_name}}_wellbore_id", record_id)

        for _ in range(2):  # create 2 logset
            record_id = build_request_seach_tests_setup_create_logsets().call(
                env, assert_status=200).get_response_obj().recordIds[0]
        env.set("setup_search_{{prefix_data_entity_name}}_logset_id", record_id)  # it doesn't matter which logset id is set

        for _ in range(2):  # create 2 marker
            build_request_seach_tests_setup_create_markers().call(env, assert_status=200)

        for _ in range(3):  # create 3 logs
            build_request_seach_tests_setup_create_logs().call(env, assert_status=200)

        # create the ref record
        build_request_seach_tests_setup_create_record_refs().call(env, assert_status=200)

        # wait for the record to be searchable
        while nb_record <= 0 and wait_attempt >= 0:
            print('not enough record indexed => Wait 1 minute ... attempt countdown=' + str(wait_attempt))
            sleep(60)
            query_result = query_for_record_set_available(env)
            nb_record = len(query_result.results)
            wait_attempt -= 1

    assert nb_record > 0, 'search setup failure, get the record set'

    # pick the first
    ref_data = query_result.results[0]
    env.set('search_{{prefix_data_entity_name}}_wellbore_id', ref_data.data.channelNames[0])
    env.set('search_{{prefix_data_entity_name}}_logset_id', ref_data.data.channelNames[1])


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_wellbores_by_distance(get_env, set_search_query_type):
    resobj = build_request_search_wellbores_by_distance().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 1


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_wellbores_by_bounding_box(get_env, set_search_query_type):
    resobj = build_request_search_wellbores_by_bounding_box().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 1


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_wellbores_by_geo_polygon(get_env, set_search_query_type):
    resobj = build_request_search_wellbores_by_geo_polygon().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 1


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logset_by_wellbore_id(get_env, set_search_query_type):
    resobj = build_request_search_logset_by_wellbore_id().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_markers_by_wellbore_id(get_env, set_search_query_type):
    resobj = build_request_search_markers_by_wellbore_id().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logset_by_wellbore_attribute(get_env, set_search_query_type):
    resobj = build_request_search_logset_by_wellbores_attribute().call(
        get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logs_by_wellbore_id(get_env, set_search_query_type):
    resobj = build_request_search_logs_by_wellbore_id().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 3


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logs_by_wellbore_attribute(get_env, set_search_query_type):
    resobj = build_request_search_logs_by_wellbores_attribute().call(
        get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 3


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logs_by_logset_id(get_env, set_search_query_type):
    resobj = build_request_search_logs_by_logset_id().call(get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 3


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logs_by_logset_attribute(get_env, set_search_query_type):
    resobj = build_request_search_logs_by_logsets_attribute().call(
        get_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 3


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_wellbores(get_env, set_search_query_type):
    build_request_search_wellbores().call(
        get_env, assert_status=200)


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logs(get_env, set_search_query_type):
    build_request_search_logs().call(
        get_env, assert_status=200)