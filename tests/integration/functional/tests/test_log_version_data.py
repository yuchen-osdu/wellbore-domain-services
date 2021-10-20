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
from wdms_client.request_builders.wdms.crud.log import *
from wdms_client.request_runner import RequestRunner, Request
from .fixtures import with_wdms_env

@pytest.fixture(scope="module")
def env_with_log_record(with_wdms_env):
    #  create the log
    result = build_request_create_log().call(with_wdms_env)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1

    with with_wdms_env.scoped_update(log_record_id=resobj.recordIds[0]):
        result = build_request_add_log_bulk_data().call(with_wdms_env)
        result.assert_ok()

        yield with_wdms_env

        # teardown: delete the log
        build_request_delete_log().call(with_wdms_env).assert_status_code(204)


def test_get_log_version_data(env_with_log_record):
    result = build_request_get_versions_of_log().call(env_with_log_record)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert len(resobj.versions) >= 1
    versions = resobj.versions[1]

    request_runner = RequestRunner(
        Request(
            name="Get log version data",
            method="GET",
            url="{{base_url}}/ddms/v2/logs/{{log_record_id}}/versions/"+str(versions)+"/data",
            headers={
                "accept": "application/json",
                "data-partition-id": "{{data_partition}}",
                "Connection": "{{header_connection}}",
                "Authorization": "Bearer {{token}}",
            },
        )
    )
    result = request_runner.call(
        env_with_log_record, assert_code=200
    )
    result.assert_ok()
    resobj = result.get_response_obj()

    assert resobj.data
    assert len(resobj.data) >= 3
    assert resobj.data[0]
    assert resobj.data[1]
    assert resobj.data[2]

    assert resobj.data[0][1] == 10
    assert resobj.data[1][1] == 20
    assert resobj.data[2][1] == 30
