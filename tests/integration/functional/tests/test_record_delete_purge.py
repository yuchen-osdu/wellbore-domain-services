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
from .test_chunking import ParquetSerializer, JsonSerializer, generate_df, build_request
from ..request_builders.wdms.crud.osdu_wellboremarkerset import build_request_create_osdu_wellboremarkerset
from ..request_builders.wdms.crud.osdu_wellboretrajectory import build_request_create_osdu_wellboretrajectory
from ..request_builders.wdms.crud.osdu_welllog import build_request_create_osdu_welllog
from ..request_builders.wdms.delete import build_request_delete_purge_record, build_request_get_record
from ..request_runner import RequestRunner

entity_type_dict = {
    "welllog": {"entity": "welllogs", "version": "v3"},
    "wellboretrajectory": {"entity": "wellboretrajectories", "version": "v3"}
}


def build_base_url(entity_type: str) -> str:
    return '{{base_url}}/ddms/' + entity_type_dict[entity_type]["version"] + '/' + entity_type_dict[entity_type][
        "entity"]


def build_request_post_data(entity_type: str, record_id: str, payload) -> RequestRunner:
    url = build_base_url(entity_type) + f'/{record_id}/data'
    return build_request(f'{entity_type} post data', 'POST', url, payload=payload)


def create_record_with_data(with_wdms_env, entity_type, serializer, nb_version):
    if entity_type == 'welllog':
        result = build_request_create_osdu_welllog(False).call(with_wdms_env)
    elif entity_type == 'wellboretrajectory':
        result = build_request_create_osdu_wellboretrajectory(False).call(with_wdms_env)

    resobj = result.get_response_obj()

    data = generate_df(['MD', 'X'], range(8))
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

    with_wdms_env.set(f'record_id', with_wdms_env.get(f'osdu_{entity_type}_record_id'))
    with_wdms_env.set('purge', 'true')
    with_wdms_env.set('v3_entity',  entity_type_dict[entity_type]["entity"])
    result = build_request_delete_purge_record().call(with_wdms_env)
    result.assert_status_code(204)
    with_wdms_env.set(f'base_url_v3_record', build_base_url(entity_type))
    result = build_request_get_record().call(with_wdms_env)
    result.assert_status_code(404)


@pytest.mark.tag('basic', 'smoke')
@pytest.mark.parametrize('serializer', [ParquetSerializer(), JsonSerializer()])
@pytest.mark.parametrize('entity_type', [entity_type for entity_type in entity_type_dict.keys()])
def test_soft_delete_purge_record(with_wdms_env, entity_type, serializer):
    create_record_with_data(with_wdms_env, entity_type, serializer, 20)

    with_wdms_env.set(f'record_id', with_wdms_env.get(f'osdu_{entity_type}_record_id'))
    with_wdms_env.set(f'purge', "false")
    with_wdms_env.set('v3_entity', entity_type_dict[entity_type]["entity"])
    result = build_request_delete_purge_record().call(with_wdms_env)
    result.assert_status_code(204)
    with_wdms_env.set(f'base_url_v3_record', build_base_url(entity_type))
    result = build_request_get_record().call(with_wdms_env)
    result.assert_status_code(404)
