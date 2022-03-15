import pytest
from unittest import mock
from fastapi import Header

from fastapi.testclient import TestClient
from odes_search.models import CursorQueryResponse
from starlette import status

from app.auth.auth import require_opendes_authorized_user
from app.clients import StorageRecordServiceClient, SearchServiceClient
from app.helper import traces
from app.middleware import require_data_partition_id
from app.routers.search.search_wrapper import SearchWrapper
from app.context import Context
from app.wdms_app import app_injector, wdms_app
from tests.unit.test_utils import create_mock_class

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)
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

URL_PARAM = [
    '/alpha/ddms/v3/query/wellbores',
    '/alpha/ddms/v3/query/wellbores/123/wellboretrajectories',
    '/alpha/ddms/v3/query/welllogs',
]
PARAMS = [
    # search response, expected response
    ({"id": "123465"}, {"id": "123465"}),
    ({"id": "123465", "other": None}, {"id": "123465"}),
]


@pytest.mark.parametrize("base_url", URL_PARAM)
@pytest.mark.parametrize("search_response, expected", PARAMS)
def test_query_results_without_none(client, base_url, search_response, expected):
    moc = mock.AsyncMock(return_value=CursorQueryResponse(results=[search_response]))
    with mock.patch.object(SearchServiceClientMock, 'query_with_cursor', moc):
        # when
        response = client.post(f'{base_url}', headers={'data-partition-id': 'testing_partition', 'names': 'dd'},
                               json={'query': 'query'})

        # then
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["results"][0] == expected
