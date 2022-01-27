import types
from typing import List

import httpx
import odes_storage
import pytest
from mock import mock
from mock.mock import AsyncMock, create_autospec

from app.clients import make_storage_record_client


@pytest.fixture(scope="module")
def local_dev_config():
    # local import
    from app.conf import Config

    # set config to a local dev config (assumption for running unit tests)
    Config.dev_mode.value = True
    Config.cloud_provider.value = "local"
    Config.service_host_search.value = "https://test-endpoint/api/search"
    Config.service_host_storage.value = "https://test-endpoint/api/storage"
    Config.modules.value = "log_recognition.routers.log_recognition"
    # This one is necessary as long as we have can_run() in modules dependending on it
    Config.environment_name.value = "evd"

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch('app.conf') as app_conf:
        app_conf.Config = Config

        yield Config


@pytest.fixture
def mock_storage_client_holding_data(local_dev_config):
    """
    Fixture mocking the Storage Client, except for a specific record that we want to return when requested.
     The data we want the Client to hold and return as the service would normally do is passed as an argument.

     For usage examples, see fixtures_test.py in this directory
    """

    def setup_data_for_mock(data):
        template_client = make_storage_record_client(
            local_dev_config.service_host_storage
        )

        # Note: we want to be able to modify the mock to handle get_record and get_record_version specifically
        mock = create_autospec(spec=template_client, instance=True)

        # override api_client to use an async mock (needed on shutdown when we call api_client.close())
        mock.api_client = AsyncMock(spec_set=template_client.api_client)

        async def mocked_get_record(self,
                             id: str,
                             data_partition_id: str = None,
                             attribute: List[str] = None,
                             appkey: str = None,
                             token: str = None) -> odes_storage.models.Record:
            # return the latest
            return await self.get_record_version(id, None, data_partition_id, appkey, token)

        async def mocked_get_record_version(self,
                                     id: str,
                                     version: int,
                                     data_partition_id: str = None,
                                     appkey: str = None,
                                     token: str = None) -> odes_storage.models.Record:
            for d in data:
                # CAREFUL: id might be optional in the model (not set on write)
                # Also storage seems to have problematic behavior with id ending in ':'
                if id is not None and (id == d.id or id + ":" == d.id):
                    if version is None or version == d.version:  # Note: version None means latest
                        return d

            # if not found, attempt to emulate behavior of the actual client
            raise odes_storage.UnexpectedResponse(
                status_code=404,
                reason_phrase="Item not found",
                # not sure what to put here at this time
                content="".encode(encoding="utf-8"),
                headers=httpx.Headers(),
            )

        # override get_record method on the instance to return sample data
        mock.get_record = types.MethodType(mocked_get_record, mock)
        mock.get_record_version = types.MethodType(mocked_get_record_version, mock)

        return mock

    return setup_data_for_mock

