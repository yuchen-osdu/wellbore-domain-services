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
    with_wdms_env.set("entity", 'logs')
    result = build_request_create_log_with_extra_fields().call(with_wdms_env)
    result.assert_ok()
    with_wdms_env.set("record_id", result.get_response_obj().recordIds[0])
    yield with_wdms_env

    build_request_clean_up_delete_log().call(with_wdms_env).assert_ok()


@pytest.mark.tag('basic', 'smoke', 'error')
def test_record_should_keep_extra_field(env_with_record_extra_created):
    result = build_request_get_record_check_for_extra_fields().call(env_with_record_extra_created)
    result.assert_ok()
    resobj = result.get_response_obj()
    assert resobj.data.xxx_extra_at_data == 'value_at_data'
    assert 'US' in resobj.legal.otherRelevantDataCountries


tests_parameters_for_relationship_extra_field = [
    ('logs', "{{logKind}}", {"relationships": {"extra_field": "EXTRA_VALUE"}}),
    ('logsets', "{{logSetKind}}", {"relationships": {"wellbore": "", "extra_field": "EXTRA_VALUE"}}),
    ('markers', "{{markerKind}}", {"name": "foo", "md": {"value": 1, "unitKey": "m"}, "relationships": {"wellbore": "", "extra_field": "EXTRA_VALUE"}}),
    ('trajectories', "{{trajectoryKind}}", {"relationships": {"wellbore": "", "extra_field": "EXTRA_VALUE"}}),
    ('dipsets', "{{dipsetKind}}", {"relationships": {"wellbore": "", "extra_field": "EXTRA_VALUE"}}),
    ('wellbores', "{{wellboreKind}}", {"relationships": {"extra_field": "EXTRA_VALUE"}}),
    ('wells', "{{wellKind}}", {"relationships": {"extra_field": "EXTRA_VALUE"}})
]
@pytest.mark.parametrize('entities, entities_kind, data_extra_field', tests_parameters_for_relationship_extra_field)
def test_relationships_extra_field(with_wdms_env, entities, entities_kind, data_extra_field):
    with_wdms_env.set("base_url_entity", entities)
    with_wdms_env.set("entity_kind", entities_kind)
    with_wdms_env.set("data", data_extra_field)
    result = build_request_create_data_extra_fields().call(with_wdms_env, assert_status=200)
    with_wdms_env.set("record_id", result.get_response_obj().recordIds[0])
    result = build_request_get_record_check_for_extra_fields().call(with_wdms_env, assert_status=200)
    resobj = result.get_response_obj()
    assert resobj.data.relationships.extra_field == 'EXTRA_VALUE'