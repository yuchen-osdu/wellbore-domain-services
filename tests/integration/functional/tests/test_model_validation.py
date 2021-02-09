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
from ..request_builders.wdms.error_cases import build_request_create_log_with_invalid_data_should_422
from ..request_builders.wdms.model_extensibility import *


def test_create_log_with_invalid_data_should_422(with_wdms_env):
    build_request_create_log_with_invalid_data_should_422().call(with_wdms_env).assert_status_code(422)


@pytest.fixture
def env_with_record_extra_created(with_wdms_env):
    result = build_request_create_log_with_extra_fields().call(with_wdms_env)
    result.assert_ok()
    with_wdms_env.set("record_id", result.get_response_obj().recordIds[0])
    yield with_wdms_env

    build_request_clean_up_delete_log().call(with_wdms_env).assert_ok()


@pytest.mark.tag('basic', 'smoke', 'error')
def test_record_should_keep_extra_field(env_with_record_extra_created):
    result = build_request_get_log_check_for_extra_fields().call(env_with_record_extra_created)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.data.xxx_extra_at_data == 'value_at_data'
    assert 'US' in resobj.legal.otherRelevantDataCountries
