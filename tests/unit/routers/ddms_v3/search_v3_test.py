from unittest.mock import create_autospec, patch

from odes_search.models import CursorQueryResponse
import pytest
from starlette import status

from app.clients import SearchServiceClient, StorageRecordServiceClient


search_service_client_mock = create_autospec(SearchServiceClient, spec_set=True, instance=True)


@pytest.fixture
def client(app_configurable_with_testclient, nope_logger_fixture):
    _, client = app_configurable_with_testclient(
        search_client_mock=search_service_client_mock
    )
    return client


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
@pytest.mark.anyio
async def test_query_results_without_none(client, base_url, search_response, expected):
    with patch.object(search_service_client_mock, 'query_with_cursor',
                      return_value=CursorQueryResponse(results=[search_response])):
        # when
        response = await client.post(f'{base_url}', headers={'data-partition-id': 'testing_partition', 'names': 'dd'},
                               json={'query': 'query'})

        # then
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["results"][0] == expected
