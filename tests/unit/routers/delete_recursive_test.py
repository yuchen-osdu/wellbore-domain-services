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

from unittest.mock import AsyncMock, patch

from fastapi import HTTPException as fastApiHTTPException, status
from odes_search.exceptions import UnexpectedResponse as clientHTTPException
from odes_search.models import CursorQueryResponse
import pytest
from starlette.exceptions import HTTPException as starletteHTTPException


from app.clients import StorageRecordServiceClient
from app.model.entity_utils import Entity, format_kind, get_kind
from app.routers.ddms_v2.storage_helper import StorageHelper

from tests.unit.test_utils import make_record, ctx_fixture

storage_record_service_client_mock = AsyncMock(spec=StorageRecordServiceClient)


@pytest.fixture(params=['authority_data_partition', 'authority_slb'])
def authority(request):
    return 'test_data_partition' if request.param == "authority_data_partition" else 'slb'


@pytest.fixture
def data_partition():
    return 'test_data_partition'


@pytest.fixture
def entity_source():
    return 'test_source'


@pytest.fixture
def well_record(authority, entity_source):
    return make_record(
        id='id:source_id',
        kind=get_kind(authority, entity_source, Entity.WELL))


@pytest.fixture
def with_patched_get_record(well_record):
    """ patch storage to return well_record of get_record call """
    with patch.object(
            storage_record_service_client_mock,
            'get_record',
            return_value=well_record):
        yield


@pytest.mark.asyncio
async def test_delete_recursive_only_delete_entity_provided(ctx_fixture,
                                                            nope_logger_fixture,
                                                            authority,
                                                            data_partition,
                                                            entity_source,
                                                            well_record,
                                                            with_patched_get_record):
    expect_delete_ids = ['id:sub1', 'id:sub2', 'id:sub3']
    entity_types = [Entity.LOGSET, Entity.MARKER]

    mocked_query_response_dict = {
        'results': [
            # expected to be delete
            {'id': expect_delete_ids[0], 'kind': get_kind(authority, entity_source, entity_types[0])},
            {'id': expect_delete_ids[1], 'kind': get_kind(authority, entity_source, entity_types[0])},
            {'id': expect_delete_ids[2], 'kind': get_kind(authority, entity_source, entity_types[1])},

            # expected to NOT be delete
            {'id': 'id:no_delete_1', 'kind': format_kind(authority, entity_source, 'otherEntity', '1')},
            {'id': 'id:no_delete_2', 'kind': format_kind(authority, entity_source, 'otherEntity', '1')},
        ]
    }
    expect_delete_ids.append(well_record.id)

    with patch('app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
               return_value=CursorQueryResponse(**mocked_query_response_dict)),\
         patch.object(storage_record_service_client_mock, 'delete_record') as moc_storage_delete_record:
        # when
        await StorageHelper.delete_recursively(
            ctx_fixture,
            well_record.id,
            'well',
            [Entity.LOGSET, Entity.MARKER],
            data_partition,
            None,
            storage_record_service_client_mock
        )

        # then
        actual_deleted_id = set([call.kwargs['id'] for call in moc_storage_delete_record.call_args_list])
        assert set(expect_delete_ids) == actual_deleted_id


@pytest.mark.asyncio
async def test_delete_failure_on_parent_dont_delete_children(ctx_fixture,
                                                             nope_logger_fixture,
                                                             authority,
                                                             data_partition,
                                                             entity_source,
                                                             well_record,
                                                             with_patched_get_record):
    # in case of exception on delete call, should still call delete on all of them

    sub_ids = [f'id:{i}' for i in range(10)]
    sub_kind = get_kind(authority, entity_source, Entity.LOGSET)
    with patch(
            'app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
            return_value=CursorQueryResponse(**{
                'results': [
                    {'id': rid, 'kind': sub_kind} for rid in sub_ids
                ]
            })),\
          patch.object(
              storage_record_service_client_mock,
              'delete_record',
              side_effect=RuntimeError('simulate error')) as moc_storage_delete_record:

        with pytest.raises(RuntimeError):  # expect to raise
            await StorageHelper.delete_recursively(
                ctx_fixture,
                well_record.id, 'well',
                [Entity.LOGSET],
                data_partition,
                None,
                storage_record_service_client_mock
            )

        # but still expected to call delete on each
        assert moc_storage_delete_record.call_count == 1
        assert moc_storage_delete_record.call_args_list[0].kwargs['id'] == well_record.id


@pytest.mark.asyncio
async def test_delete_should_keep_delete_heterogeneous_failure(
        ctx_fixture,
        nope_logger_fixture,
        authority,
        data_partition,
        entity_source,
        well_record,
        with_patched_get_record):
    # in case of exception on delete call, should still call delete on all of them

    sub_ids = [f'id:{i}' for i in range(10)]
    sub_kind = get_kind(authority, entity_source, Entity.LOGSET)
    expect_delete_ids = sub_ids + [well_record.id]
    with patch(
            'app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
            return_value=CursorQueryResponse(**{
                'results': [
                    {'id': rid, 'kind': sub_kind} for rid in sub_ids
                ]
            })
    ):
        async def delete_success_only_well(*args, **kwargs):
            if kwargs['id'] == 'id:0':
                raise starletteHTTPException(status_code=401, detail='UNAUTHORIZED')
            if kwargs['id'] != well_record.id:
                raise RuntimeError('simulate error')

        with patch.object(
                storage_record_service_client_mock, 'delete_record',
                side_effect=delete_success_only_well) as moc_storage_delete_record:
            with pytest.raises(fastApiHTTPException) as exp_info:  # expect to raise
                await StorageHelper.delete_recursively(
                    ctx_fixture,
                    well_record.id, 'well',
                    [Entity.LOGSET],
                    data_partition,
                    None,
                    storage_record_service_client_mock
                )

            # the status status is 500
            assert exp_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

            # but still expected to call delete on each
            actual_deleted_id = set([call.kwargs['id'] for call in moc_storage_delete_record.call_args_list])
            assert set(expect_delete_ids) == actual_deleted_id

            # check error are logged
            assert nope_logger_fixture.error.call_count == len(sub_ids)


@pytest.mark.asyncio
async def test_delete_should_keep_delete_homogenous_failure(
        ctx_fixture,
        nope_logger_fixture,
        authority,
        data_partition,
        entity_source,
        well_record,
        with_patched_get_record):

    # in case of exception on delete call, should still call delete on all of them

    sub_ids = [f'id:{i}' for i in range(10)]
    sub_kind = get_kind(authority, entity_source, Entity.LOGSET)
    expect_delete_ids = sub_ids + [well_record.id]
    with patch(
            'app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
            return_value=CursorQueryResponse(**{
                'results': [
                    {'id': rid, 'kind': sub_kind} for rid in sub_ids
                ]
            })
    ):
        async def delete_success_only_well(*args, **kwargs):
            if kwargs['id'] != well_record.id:
                raise starletteHTTPException(status_code=403, detail="Forbidden")

        with patch.object(
                storage_record_service_client_mock, 'delete_record',
                side_effect=delete_success_only_well) as moc_storage_delete_record:
            with pytest.raises(fastApiHTTPException) as exp_info:  # expect to raise
                await StorageHelper.delete_recursively(
                    ctx_fixture,
                    well_record.id, 'well',
                    [Entity.LOGSET],
                    data_partition,
                    None,
                    storage_record_service_client_mock
                )

            # the status status is kept
            assert exp_info.value.status_code == status.HTTP_403_FORBIDDEN

            # but still expected to call delete on each
            actual_deleted_id = set([call.kwargs['id'] for call in moc_storage_delete_record.call_args_list])
            assert set(expect_delete_ids) == actual_deleted_id

            # check error are logged
            assert nope_logger_fixture.error.call_count == len(sub_ids)


@pytest.mark.asyncio
@pytest.mark.parametrize('exception', [starletteHTTPException(status_code=status.HTTP_404_NOT_FOUND),
                                       fastApiHTTPException(status_code=status.HTTP_404_NOT_FOUND),
                                       clientHTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                                           reason_phrase='',
                                                           content=b'',
                                                           headers={})])
async def test_delete_404_of_sub_delete_is_valid(ctx_fixture,
                                                 nope_logger_fixture,
                                                 data_partition,
                                                 authority,
                                                 entity_source,
                                                 well_record,
                                                 with_patched_get_record,
                                                 exception):
    with patch(
            'app.routers.search.search_wrapper.SearchWrapper.query_cursorless',
            return_value=CursorQueryResponse(**{
                'results': [
                    {'id': 'id:sub',
                     'kind': get_kind(authority, entity_source, Entity.LOGSET)}]
            })
    ):
        async def delete_success_only_well(*args, **kwargs):
            print(args)
            print(kwargs)
            if kwargs['id'] != well_record.id:
                raise exception

        with patch.object(
                storage_record_service_client_mock, 'delete_record',
                side_effect=delete_success_only_well):
            # no exception raised
            await StorageHelper.delete_recursively(
                ctx_fixture,
                well_record.id, 'well',
                [Entity.LOGSET],
                data_partition,
                None,
                storage_record_service_client_mock)


@pytest.mark.asyncio
@pytest.mark.parametrize('exception',
                         [fastApiHTTPException(status_code=status.HTTP_403_FORBIDDEN),
                          fastApiHTTPException(status_code=status.HTTP_404_NOT_FOUND),
                          fastApiHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR),
                          RuntimeError()])
async def test_delete_failure_get_record(ctx_fixture,
                                         nope_logger_fixture,
                                         data_partition,
                                         entity_source,
                                         well_record,
                                         exception):
    with patch.object(storage_record_service_client_mock, 'get_record', side_effect=exception):
        with pytest.raises(exception.__class__):
            await StorageHelper.delete_recursively(
                ctx_fixture,
                well_record.id, 'well', [],
                data_partition, None, storage_record_service_client_mock)
