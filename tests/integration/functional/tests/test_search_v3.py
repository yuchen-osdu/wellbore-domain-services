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
from ..request_builders.wdms.search_apis.setup import *
from ..request_builders.wdms.search_apis.search import *
from time import sleep

@pytest.fixture(params=['query', 'fastquery'])
def set_search_query_type(with_wdms_env, request):
    env = with_wdms_env
    env.set('search_query_type', request.param)

def query_for_record_set_available(env):
    result = build_request_osdu_seach_tests_setup_start().call(env)
    result.assert_ok()
    return result.get_response_obj()
    # return result.response.json()

@pytest.mark.tag('search')
@pytest.mark.dependency()
def test_setup_for_search(with_wdms_env):
    # TODO this must be revisited to have independent setup for each needed record
    wait_attempt = 10

    # set here the version the data set of record needed for the tests
    env = with_wdms_env
    env.set('search_record_version', '0001')
    # this value is use in the query to fetch the record

    env.set('search_query_type', 'fastquery')

    query_result = query_for_record_set_available(env)
    nb_record = len(query_result.results)
    if nb_record > 0:
        #Retrieve wellboreID
        env.set("setup_search_osdu_wellbore_id", query_result.results[0].data.WellboreID)

    if nb_record == 0:
        # create one wellbore
        record_id = build_request_seach_tests_setup_create_osdu_wellbore().call(
            env, assert_status=200).get_response_obj().recordIds[0]
        env.set("setup_search_osdu_wellbore_id", record_id)

        for _ in range(2):  # create 2 logset
            record_id = build_request_seach_tests_setup_create_osdu_welllogs().call(
                env, assert_status=200).get_response_obj().recordIds[0]
        env.set("setup_search_osdu_welllog_id", record_id)  # it doesn't matter which logset id is set

        for _ in range(2):  # create 2 marker
            build_request_seach_tests_setup_create_osdu_markersets().call(env, assert_status=200)

        # wait for the record to be searchable
        while nb_record <= 0 and wait_attempt >= 0:
            print('not enough record indexed => Wait 1 minute ... attempt countdown=' + str(wait_attempt))
            sleep(60)
            query_result = query_for_record_set_available(env)
            nb_record = len(query_result.results)
            wait_attempt -= 1

    assert nb_record > 0, 'search setup failure, get the record set'

@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_welllogs_by_wellbore_id(with_wdms_env, set_search_query_type):
    resobj = build_request_search_welllogs_by_wellbore_id().call(with_wdms_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_markersets_by_wellbore_id(with_wdms_env, set_search_query_type):
    resobj = build_request_search_markersets_by_wellbore_id().call(with_wdms_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_logset_by_wellbore_attribute(with_wdms_env, set_search_query_type):
    resobj = build_request_search_welllogs_by_wellbores_attribute().call(
        with_wdms_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 2


@pytest.mark.tag('search')
@pytest.mark.dependency(depends=["test_setup_for_search"])
def test_search_wellbore_by_name(with_wdms_env):
    #Only search and no fast search
    env = with_wdms_env
    env.set('search_query_type', 'query')
    resobj = build_request_search_wellbore_by_name().call(with_wdms_env, assert_status=200).get_response_obj()
    assert resobj.totalCount >= 1
