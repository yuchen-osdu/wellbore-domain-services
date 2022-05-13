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
from wdms_client.request_builders.wdms.crud.osdu_welllog import (
    build_request_create_osdu_welllog,
    build_request_delete_osdu_welllog)
from wdms_client.request_builders.wdms.session import (
    build_create_session,
    build_delete_session,
    build_get_session,
    build_list_session, build_create_session_empty_payload)


SESSION_URL_PREFIX = 'alpha/ddms/v3/welllogs'


@pytest.fixture
def with_welllog(with_wdms_env):
    b_use_fixed_id = False
    result = build_request_create_osdu_welllog(b_use_fixed_id).call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert len(resobj.recordIds) == 1

    # TODO: when we have the version in the response must return as well
    record_id = resobj.recordIds[0]

    yield record_id

    build_request_delete_osdu_welllog(record_id).call(with_wdms_env)


def create_session(env, record_id, meta=None):
    result = build_create_session(record_id, SESSION_URL_PREFIX, meta=meta).call(env)
    result.assert_ok()
    return result.get_response_obj()


@pytest.mark.parametrize('payload', [(None), ({})])
@pytest.mark.tag('session', 'smoke', 'chunking')
def test_create_session_empty_payload(with_wdms_env, with_welllog, payload):
    record_id = with_welllog
    result = build_create_session_empty_payload(record_id, SESSION_URL_PREFIX, payload).call(with_wdms_env)
    result.assert_status_code(422)

@pytest.mark.tag('session', 'smoke', 'chunking')
def test_create_get_session(with_wdms_env, with_welllog):
    record_id = with_welllog
    session_obj = create_session(with_wdms_env, record_id, meta={'custom': 'from_e2e'})

    assert session_obj.recordId
    assert session_obj.state == 'open'
    assert session_obj.meta.custom == 'from_e2e'

    session_obj = build_get_session(record_id,
                                    SESSION_URL_PREFIX,
                                    session_obj.id).call(with_wdms_env, assert_status=200).get_response_obj()
    assert session_obj.recordId
    assert session_obj.state == 'open'
    assert session_obj.meta.custom == 'from_e2e'

    build_delete_session(record_id, SESSION_URL_PREFIX, session_obj.id).call(with_wdms_env).assert_ok()


@pytest.mark.tag('session', 'smoke', 'chunking')
def test_list_session(with_wdms_env, with_welllog):
    r_id = with_welllog

    # create a session
    session1_obj = create_session(with_wdms_env, r_id, meta={'key': 'session1'})

    # list with a single session
    sessions = build_list_session(r_id, SESSION_URL_PREFIX).call(with_wdms_env, assert_status=200).get_response_obj()
    assert len(sessions) == 1
    assert sessions[0].meta.key == 'session1'

    # create a second session
    session2_obj = create_session(with_wdms_env, r_id, meta={'key': 'session2'})

    # list with two sessions
    sessions = build_list_session(r_id, SESSION_URL_PREFIX).call(with_wdms_env, assert_status=200).get_response_obj()
    assert len(sessions) == 2
    sessions = {s.id: s for s in sessions}
    assert sessions[session1_obj.id].meta.key == 'session1'
    assert sessions[session2_obj.id].meta.key == 'session2'

    # clean up
    build_delete_session(r_id, SESSION_URL_PREFIX, session1_obj.id).call(with_wdms_env).assert_ok()
    build_delete_session(r_id, SESSION_URL_PREFIX, session2_obj.id).call(with_wdms_env).assert_ok()
