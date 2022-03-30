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

from wdms_client.request_builders.wdms.crud.osdu_wellboretrajectory import build_request_create_osdu_wellboretrajectory
from wdms_client.request_builders.wdms.crud.osdu_welllog import build_request_create_osdu_welllog
from .fixtures import with_wdms_env
from .test_chunking import ParquetSerializer, JsonSerializer, generate_df, build_request
from wdms_client.request_builders.wdms.delete import build_request_delete_purge_record, build_request_get_record
from wdms_client.request_runner import RequestRunner

entity_type_dict = {
    "welllog": "welllogs",
    "wellboretrajectory": "wellboretrajectories"
}


def build_request_post_data(entity_type: str, record_id: str, payload) -> RequestRunner:
    url = '{{base_url}}/ddms/v3/' + entity_type_dict[entity_type] + f'/{record_id}/data'
    return build_request(f'{entity_type} post data', 'POST', url, payload=payload)


def create_record_with_data(with_wdms_env, entity_type, serializer, nb_version):
    col = ['MD', 'X']
    if entity_type == 'welllog':
        result = build_request_create_osdu_welllog(False, col).call(with_wdms_env)
    elif entity_type == 'wellboretrajectory':
        result = build_request_create_osdu_wellboretrajectory(False, col).call(with_wdms_env)

    result.assert_ok()
    resobj = result.get_response_obj()

    data = generate_df(col, range(8))
    data_to_send = serializer.dump(data)
    headers = {'Content-Type': serializer.mime_type, 'Accept': serializer.mime_type}

    # DATA
    for i in range(nb_version):
        build_request_post_data(entity_type, resobj.recordIds[0], data_to_send).call(with_wdms_env,
                                                                                     headers=headers).assert_ok()

    assert resobj.recordCount == 1
    assert len(resobj.recordIds) == 1
    with_wdms_env.set(f'osdu_{entity_type}_record_id',
                      resobj.recordIds[0])  # stored the record id for the following tests


@pytest.mark.tag('basic', 'smoke')
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
@pytest.mark.parametrize('entity_type', [entity_type for entity_type in entity_type_dict.keys()])
def test_hard_delete_purge_record(with_wdms_env, entity_type, serializer):
    create_record_with_data(with_wdms_env, entity_type, serializer, 20)

    record_id = with_wdms_env.get(f'osdu_{entity_type}_record_id')
    purge = 'true'
    v3_entity = entity_type_dict[entity_type]
    result = build_request_delete_purge_record(record_id, v3_entity, purge).call(with_wdms_env)
    result.assert_status_code(204)
    base_url_v3_record = '{{base_url}}/ddms/v3/' + entity_type_dict[entity_type]
    result = build_request_get_record(base_url_v3_record, record_id).call(with_wdms_env)
    result.assert_status_code(404)


@pytest.mark.tag('basic', 'smoke')
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
@pytest.mark.parametrize('entity_type', [entity_type for entity_type in entity_type_dict.keys()])
def test_soft_delete_purge_record(with_wdms_env, entity_type, serializer):
    create_record_with_data(with_wdms_env, entity_type, serializer, 20)

    record_id = with_wdms_env.get(f'osdu_{entity_type}_record_id')
    purge = 'false'
    v3_entity = entity_type_dict[entity_type]
    result = build_request_delete_purge_record(record_id, v3_entity, purge).call(with_wdms_env)
    result.assert_status_code(204)
    base_url_v3_record = '{{base_url}}/ddms/v3/' + entity_type_dict[entity_type]
    result = build_request_get_record(base_url_v3_record, record_id).call(with_wdms_env)
    result.assert_status_code(404)
