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

import mock
import pytest

from fastapi import HTTPException, Header, status
from fastapi.testclient import TestClient
from odes_search.models import CursorQueryResponse
from odes_storage.models import RecordVersions, CreateUpdateRecordsResponse, Record

from app.auth.auth import require_opendes_authorized_user
from app.clients import *
from app.helper import traces
from app.middleware import require_data_partition_id
from app.model.entity_utils import Entity
from app.model.model_curated import *
from app.model.osdu_model import Wellbore, Well, WellLog
from app.routers.ddms_v2.storage_helper import StorageHelper
from app.routers.search.search_wrapper import SearchWrapper
from app.utils import Context
from app.wdms_app import wdms_app, app_injector
from tests.unit.test_utils import create_mock_class, make_record, nope_logger_fixture

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
            kind="namespace:osdu:Wellbore:2.7.112",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        )),
    ('/ddms/v3/wells', Well(
        id=r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:Well:2.7.112",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={},
    )),
    ('/ddms/v3/welllogs', WellLog(
        id=r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9",
        kind="namespace:osdu:WellLog:2.7.112",
        acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        legal={
            "legaltags": ["string"],
            "otherRelevantDataCountries": ["FR"],
        },
        data={},
    )),
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

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)
StorageHelperMock = create_mock_class(StorageHelper)
SearchWrapperMock = create_mock_class(SearchWrapper)


@pytest.fixture
def client(nope_logger_fixture):
    async def bypass_authorization():
        # empty method
        pass

    async def set_default_partition(data_partition_id: str = Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    async def build_mock_storage():
        return StorageRecordServiceClientMock()

    async def build_mock_search():
        return SearchServiceClientMock()

    app_injector.register(StorageRecordServiceClient, build_mock_storage)
    app_injector.register(SearchServiceClient, build_mock_search)

    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_success(client, base_url, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc):
        # when
        response = client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=record_id, data_partition_id='testing_partition')

        # assert it validates the input object schema
        record_obj.validate(response.json())

@pytest.mark.parametrize('base_url, record_obj', tests_errors_422)
def test_get_record_422(client, base_url, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc):
        # when
        response = client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=record_id, data_partition_id='testing_partition')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_without_default_values(client, base_url, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc):
        # when
        response = client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # assert we retrieve only the input fields
        assert(response.json() == record_obj.dict(exclude_unset=True))


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_not_found_case(client, base_url, record_obj):
    record_id = record_obj.id
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    # the following doesn't work, do not raise but return AsyncMock instead:
    # with mock.patch.object(StorageRecordServiceClientMock, 'get_record', mock.AsyncMock(side_effect=record_obj)):

    with StorageRecordServiceClientMock.set_throw('get_record', exception):
        # when
        response = client.get(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.text.lower()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_delete_record_successful(client, base_url, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock()

    with mock.patch.object(StorageRecordServiceClientMock, 'delete_record', moc):
        response = client.delete(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=record_id, data_partition_id='testing_partition')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_delete_recursive_record_with_recursive_not_in_query_successful(client, base_url, record_obj):
    record_id = record_obj.id

    with mock.patch.object(StorageRecordServiceClientMock, 'delete_record',
                           wraps=StorageRecordServiceClientMock.delete_record) as mock_storage:
        with mock.patch.object(SearchServiceClientMock, 'query_with_cursor',
                               wraps=SearchServiceClientMock.query_with_cursor) as mock_search:
            # when
            response = client.delete(f'{base_url}/{record_id}', headers={'data-partition-id': 'testing_partition'})
            # then
            mock_storage.assert_called_with(id=record_id, data_partition_id='testing_partition')
            assert not mock_search.called
            assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_delete_recursive_record_with_recursive_false_successful(client, base_url, record_obj):
    record_id = record_obj.id
    with mock.patch.object(StorageRecordServiceClientMock, 'delete_record',
                           wraps=StorageRecordServiceClientMock.delete_record) as mock_storage:
        with mock.patch.object(SearchServiceClientMock, 'query_with_cursor',
                               wraps=SearchServiceClientMock.query_with_cursor) as mock_search:
            # when
            response = client.delete(f'{base_url}/{record_id}',
                                     headers={'data-partition-id': 'testing_partition'}, params={'recursive': False})
            # then
            mock_storage.assert_called_with(id=record_id, data_partition_id='testing_partition')
            assert not mock_search.called
            assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.parametrize('base_url, record_obj', tests_parameters_for_recursive)
def test_delete_recursive_record_with_recursive_true_successful(client, base_url, record_obj):
    record_id = record_obj.id

    with mock.patch('app.routers.ddms_v2.storage_helper.StorageHelper.delete_recursively') as moc_delete_rec:
        client.delete(f'{base_url}/{record_id}',
                      headers={'data-partition-id': 'testing_partition'}, params={'recursive': True})
        moc_delete_rec.assert_called_once()


@pytest.mark.parametrize('base_url, record_obj', tests_parameters_for_recursive)
def test_delete_recursive_record_with_recursive_true_successful_delete_multiple_records(client, base_url, record_obj):
    record_id = record_obj.id
    mocked_query_response = CursorQueryResponse(**{'results': [{'id': 'id:one', 'kind': 'data-partition:wks:log:1.0.5'},
                                                               {'id': 'id:two',
                                                                'kind': 'data-partition:wks:log:1.0.5'}]})
    with mock.patch(
            'app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
            return_value=mocked_query_response
    ):
        with mock.patch.object(
                StorageRecordServiceClientMock, 'get_record',
                return_value=record_obj
        ):
            with mock.patch.object(
                    StorageRecordServiceClientMock, 'delete_record',
                    wraps=StorageRecordServiceClientMock.delete_record) as moc_storage_delete_record:
                client.delete(f'{base_url}/{record_id}',
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
def test_delete_recursive_check_sub_deleted_type(client, base_url, sub_entity_list):
    with mock.patch(
            'app.routers.ddms_v2.storage_helper.StorageHelper.delete_recursively',
            return_value=None
    ) as moc_delete_recursively:
        client.delete(f'{base_url}/123',
                      headers={'data-partition-id': 'dp'},
                      params={'recursive': True})
        assert set(moc_delete_recursively.call_args.kwargs['entity_list']) == set(sub_entity_list)


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_versions_successful(client, base_url, record_obj):
    record_id = record_obj.id
    expect_response = RecordVersions(recordId='123456', versions=["12356", "89693"])
    moc_get_all_record_versions = mock.AsyncMock(return_value=expect_response)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_all_record_versions', moc_get_all_record_versions):
        # when
        response = client.get(f'{base_url}/{record_id}/versions', headers={'data-partition-id': 'testing_partition'})

        # then
        assert response.status_code == status.HTTP_200_OK
        assert RecordVersions.parse_raw(response.text) == expect_response
        moc_get_all_record_versions.assert_called_with(id=record_id, data_partition_id='testing_partition')


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_versions_errors(client, base_url, record_obj):
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    with StorageRecordServiceClientMock.set_throw('get_all_record_versions', exception):
        # when
        response = client.get(f'{base_url}/{record_obj.id}/versions',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == exception.status_code
        assert exception.detail in response.text


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_at_version_successful(client, base_url, record_obj):
    record_id = record_obj.id
    record_obj.version = 1337

    moc_get_record_version = mock.AsyncMock(return_value=record_obj)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record_version', moc_get_record_version):
        # when
        response = client.get(f'{base_url}/{record_id}/versions/{record_obj.version}',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        moc_get_record_version.assert_called_with(id=record_id,
                                                  version=record_obj.version,
                                                  data_partition_id='testing_partition')

        # assert it validates the input object schema
        response_obj = record_obj.validate(response.json())
        assert response_obj.version == record_obj.version

@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_at_version_successful_without_default_values(client, base_url, record_obj):
    record_id = record_obj.id
    record_obj.version = 1337

    moc_get_record_version = mock.AsyncMock(return_value=record_obj)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record_version', moc_get_record_version):
        # when
        response = client.get(f'{base_url}/{record_id}/versions/{record_obj.version}',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == status.HTTP_200_OK

        # assert we retrieve only the input fields
        assert(response.json() == record_obj.dict(exclude_unset=True))

@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_get_record_at_version_errors(client, base_url, record_obj):
    exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    with StorageRecordServiceClientMock.set_throw('get_record_version', exception):
        # when
        response = client.get(f'{base_url}/{record_obj.id}/versions/1337',
                              headers={'data-partition-id': 'testing_partition'})
        assert response.status_code == exception.status_code
        assert exception.detail in response.text


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_post_records_successful(client, base_url, record_obj):
    expected_response = CreateUpdateRecordsResponse(recordCount=2, recordIds=['rec1', 'rec2'])

    # done this way because of the current inconsistency of root fields between wdms model vs storage client model
    record_dict_list = [
        make_record(True, **(record_obj.dict(exclude_unset=True))) for _ in expected_response.record_ids
    ]

    moc_create_or_update_records = mock.AsyncMock(return_value=expected_response)

    with mock.patch.object(StorageRecordServiceClientMock, 'create_or_update_records', moc_create_or_update_records):
        # when
        response = client.post(base_url, data=json.dumps(record_dict_list))

        # then
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


@pytest.mark.parametrize('base_url, record_obj', tests_parameters)
def test_post_records_error_invalid_data(client, base_url, record_obj):
    response = client.post(base_url, data=json.dumps([{"invalid": "data"}]))
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
