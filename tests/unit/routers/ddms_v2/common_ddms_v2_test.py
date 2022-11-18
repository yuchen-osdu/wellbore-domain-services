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
from unittest.mock import create_autospec, patch

from fastapi import HTTPException, status
from odes_search.models import CursorQueryResponse
from odes_storage import UnexpectedResponse
from odes_storage.models import (
    CreateUpdateRecordsResponse,
    Record,
    RecordVersions,
)
import pytest
from tests.unit.test_utils import make_record


from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.model.entity_utils import Entity
from app.model.model_curated import *
from app.model.osdu_model import (
    Well,
    Wellbore,
    WellboreMarkerSet,
    WellboreMarkerSet110,
    WellboreTrajectory,
    WellLog,
)
from app.wdms_app import app_injector, wdms_app

"""
Contains unified common tests for the different kind. Mainly CRUD test cases
"""

tests_parameters = [
    ('/ddms/v2/logs', log(id='123456', data={})),
    ('/ddms/v2/logsets', logset(id='123456', data={})),
    ('/ddms/v2/dipsets', dipset(id="123456", data={})),
    ('/ddms/v2/markers', marker(acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
                                kind='opendes:wks:marker:1.0.4',
                                legal=Legal(),
                                data=markerData(md=ValueWithUnit(value=1.0, unitKey='m'), name='name'),
                                id='123456')),
    ('/ddms/v2/trajectories', trajectory(id='123456', data={})),
    ('/ddms/v2/wellbores', wellbore(id='123456', data={})),
    ('/ddms/v2/wells', well(id='123456', data={})),
    ('/ddms/v3/wellbores',         Wellbore(
            id=r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
            kind="namespace:osdu:master-data--Wellbore:1.0.0",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        )),
    ('/ddms/v3/wells', Well(
        id=r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:master-data--Well:1.0.0",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={},
    )),
    ('/ddms/v3/welllogs', WellLog(
        id=r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:work-product-component--WellLog:1.2.0",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={},
    )),
    ('/ddms/v3/wellboremarkersets', WellboreMarkerSet(
        id=r"namespace:work-product-component--WellboreMarkerSet:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:work-product-component--WellboreMarkerSet:1.1.0",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={
            "WellboreID": r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
        },
    )),
    ('/ddms/v3/wellboremarkersets', WellboreMarkerSet110(
        id=r"namespace:work-product-component--WellboreMarkerSet:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:work-product-component--WellboreMarkerSet:1.1.0",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={
            "WellboreID": r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
        },
    )),
    ('/ddms/v3/wellboretrajectories', WellboreTrajectory(
        id=r"namespace:work-product-component--WellboreTrajectory:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:work-product-component--WellboreTrajectory:1.0.0",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={
            "WellboreID": r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:456",
            "TopDepthMeasuredDepth": 12.3,
            "BaseDepthMeasuredDepth": 11.3,
            "VerticalMeasurement": {}
        },
    ))
]

tests_errors_422 = [
    ('/ddms/v2/wellbores', Record(id='123456', kind='xx', acl={'viewers': [], 'owners': []}, legal={},
                                  data={"wellborePurpose": "develpment"})),
]

tests_parameters_for_recursive = [
    ('/ddms/v2/logsets', logset(id='123456', data={})),
    ('/ddms/v2/dipsets', dipset(id="123456", data={})),
    ('/ddms/v2/wellbores', wellbore(id='123456', data={})),
    ('/ddms/v2/wells', well(id='123456', data={}))
]


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)
search_service_client_mock = create_autospec(SearchServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(nope_logger_fixture, app_configurable_with_testclient):
    _, client = app_configurable_with_testclient(
        search_client_mock=search_service_client_mock,
        storage_client_mock=storage_record_service_client_mock
    )
    return client


def assert_called_once_with_partial(mock_inst, **expected_kwargs):
    """ because mock.assert_called_with strictly match all parameters including the one with default value """

    mock_inst.assert_called_once()
    _, call_kwargs = mock_inst.call_args_list[0]
    for k, v in expected_kwargs.items():
        assert call_kwargs[k] == v


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_success(client, base_url, record_obj):
    record_id = record_obj.id

    with patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj) as moc:
        # when
        response = await client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        assert_called_once_with_partial(moc, id=record_id, data_partition_id='testing_partition')

        # assert it validates the input object schema
        record_obj.validate(response.json())


@pytest.mark.parametrize('base_url, record_obj', tests_errors_422)
@pytest.mark.anyio
async def test_get_record_422(client, base_url, record_obj):
    record_id = record_obj.id

    with patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj) as moc:
        # when
        response = await client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=record_id, data_partition_id='testing_partition')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_without_default_values(client, base_url, record_obj):
    record_id = record_obj.id
    with patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj):
        # when
        response = await client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # assert we retrieve only the input fields
        assert(response.json() == record_obj.dict(exclude_unset=True))


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_not_found_case(client, base_url, record_obj):
    record_id = record_obj.id
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    with patch.object(storage_record_service_client_mock, 'get_record', side_effect=exception):
        # when
        response = await client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.text.lower()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_delete_record_successful(client, base_url, record_obj):
    record_id = record_obj.id

    with patch.object(storage_record_service_client_mock, 'delete_record') as moc:
        response = await client.delete(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=record_id, data_partition_id='testing_partition')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_delete_recursive_record_with_recursive_not_in_query_successful(client, base_url, record_obj):
    record_id = record_obj.id

    with patch.object(storage_record_service_client_mock, 'delete_record') as mock_storage,\
            patch.object(search_service_client_mock, 'query_with_cursor') as mock_search:
        # when
        response = await client.delete(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        # then
        mock_storage.assert_called_with(id=record_id, data_partition_id='testing_partition')
        assert not mock_search.called
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_delete_recursive_record_with_recursive_false_successful(client, base_url, record_obj):
    record_id = record_obj.id
    with patch.object(storage_record_service_client_mock, 'delete_record') as mock_storage,\
            patch.object(search_service_client_mock, 'query_with_cursor') as mock_search:
        # when
        response = await client.delete(f'{base_url}/{record_id}',
                                 headers={'data-partition-id': 'testing_partition'},
                                 params={'recursive': False})
        # then
        mock_storage.assert_called_with(id=record_id, data_partition_id='testing_partition')
        assert not mock_search.called
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize('base_url, record_obj', tests_parameters_for_recursive)
@pytest.mark.anyio
async def test_delete_recursive_record_with_recursive_true_successful(client, base_url, record_obj):
    record_id = record_obj.id

    with patch('app.routers.ddms_v2.storage_helper.StorageHelper.delete_recursively') as moc_delete_rec:
        await client.delete(f'{base_url}/{record_id}',
                      headers={'data-partition-id': 'testing_partition'}, params={'recursive': True})
        moc_delete_rec.assert_called_once()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters_for_recursive)
@pytest.mark.anyio
async def test_delete_recursive_record_with_recursive_true_successful_delete_multiple_records(client, base_url, record_obj):
    record_id = record_obj.id
    mocked_query_response = CursorQueryResponse(**{'results': [{'id': 'id:one', 'kind': 'data-partition:wks:log:1.0.5'},
                                                               {'id': 'id:two',
                                                                'kind': 'data-partition:wks:log:1.0.5'}]})
    with patch('app.routers.search.search_wrapper.SearchWrapper.query_cursorless', return_value=mocked_query_response),\
            patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj),\
            patch.object(storage_record_service_client_mock, 'delete_record') as moc_storage_delete_record:
        await client.delete(f'{base_url}/{record_id}',
                      headers={'data-partition-id': 'testing_partition'},
                      params={'recursive': True})
        # number of calls to delete_record is 3 because the record has 2 children
        # delete recursive will the record and 2 children makes it 3 calls
        assert moc_storage_delete_record.call_count == 3


@pytest.mark.parametrize('base_url, sub_entity_list', [
    ('/ddms/v2/logsets', [Entity.LOG]),
    ('/ddms/v2/dipsets', [Entity.LOG]),
    ('/ddms/v2/wellbores', [Entity.LOGSET,
                            Entity.LOG,
                            Entity.MARKER]),
    ('/ddms/v2/wells', [Entity.WELLBORE,
                        Entity.LOGSET,
                        Entity.LOG,
                        Entity.MARKER,
                        Entity.TRAJECTORY,
                        Entity.DIPSET])
])
@pytest.mark.anyio
async def test_delete_recursive_check_sub_deleted_type(client, base_url, sub_entity_list):
    with patch('app.routers.ddms_v2.storage_helper.StorageHelper.delete_recursively') as moc_delete_recursively:
        await client.delete(f'{base_url}/123',
                      headers={'data-partition-id': 'dp'},
                      params={'recursive': True})
        assert set(moc_delete_recursively.call_args.kwargs['entity_list']) == set(sub_entity_list)


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_versions_successful(client, base_url, record_obj):
    record_id = record_obj.id
    expect_response = RecordVersions(recordId='123456', versions=["12356", "89693"])

    # Because test parameter include v3 routes which calls 'get_record'
    # and I would like to avoid mocking if not needed for instance in v2 test
    patcher = None
    if "v3" in base_url:
        patcher = patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj)
        patcher.start()

    try:
        with patch.object(storage_record_service_client_mock, 'get_all_record_versions', return_value=expect_response) as moc:
            # when
            response = await client.get(f'{base_url}/{record_id}/versions', headers={'data-partition-id': 'testing_partition'})

            # then
            assert response.status_code == status.HTTP_200_OK
            assert RecordVersions.parse_raw(response.text) == expect_response
            moc.assert_called_with(id=record_id, data_partition_id='testing_partition')
    finally:
        if patcher:
            patcher.stop()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_versions_errors(client, base_url, record_obj):
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    # Because test parameter include v3 routes which calls 'get_record'
    # and I would like to avoid mocking if not needed for instance in v2 test
    patcher = None
    if "v3" in base_url:
        patcher = patch.object(storage_record_service_client_mock, 'get_record', return_value=record_obj)
        patcher.start()

    try:
        with patch.object(storage_record_service_client_mock, 'get_all_record_versions', side_effect=exception):
            # when
            response = await client.get(f'{base_url}/{record_obj.id}/versions',
                                  headers={'data-partition-id': 'testing_partition'})
            assert response.status_code == exception.status_code
            assert exception.detail in response.text
    finally:
        if patcher:
            patcher.stop()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_at_version_successful(client, base_url, record_obj):
    record_id = record_obj.id
    record_obj.version = 1337

    with patch.object(storage_record_service_client_mock, 'get_record_version', return_value=record_obj) as moc:
        # when
        response = await client.get(f'{base_url}/{record_id}/versions/{record_obj.version}',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        assert_called_once_with_partial(moc,
                                        id=record_id,
                                        version=record_obj.version,
                                        data_partition_id='testing_partition')

        # assert it validates the input object schema
        response_obj = record_obj.validate(response.json())
        assert response_obj.version == record_obj.version


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_at_version_successful_without_default_values(client, base_url, record_obj):
    record_id = record_obj.id
    record_obj.version = 1337

    with patch.object(storage_record_service_client_mock, 'get_record_version', return_value=record_obj):
        # when
        response = await client.get(f'{base_url}/{record_id}/versions/{record_obj.version}',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # assert we retrieve only the input fields
        assert(response.json() == record_obj.dict(exclude_unset=True))


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_get_record_at_version_errors(client, base_url, record_obj):
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    with patch.object(storage_record_service_client_mock, 'get_record_version', side_effect=exception):
        # when
        response = await client.get(f'{base_url}/{record_obj.id}/versions/1337',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == exception.status_code
        assert exception.detail in response.text


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_post_records_successful(client, base_url, record_obj):
    expected_response = CreateUpdateRecordsResponse(recordCount=2, recordIds=['rec1', 'rec2'])

    # done this way because of the current inconsistency of root fields between wdms model vs storage client model
    record_dict_list = [
        make_record(True, **(record_obj.dict(exclude_unset=True))) for _ in expected_response.record_ids
    ]
    with patch.object(storage_record_service_client_mock, "get_record",
                      side_effect=UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND,
                                                     reason_phrase="", content=None, headers=None)), \
         patch.object(storage_record_service_client_mock, 'create_or_update_records', return_value=expected_response):
        # when
        response = await client.post(base_url, data=json.dumps(record_dict_list), headers={'content-type': 'application/json'})

        # then
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
@pytest.mark.anyio
async def test_post_records_error_invalid_data(client, base_url, record_obj):
    response = await client.post(base_url, data=json.dumps([{"invalid": "data"}]))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
