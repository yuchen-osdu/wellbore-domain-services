import asyncio
import contextlib
import copy
import types
from typing import List


import httpx
import odes_storage
import pytest
from unittest import mock
from unittest.mock import AsyncMock, create_autospec

from fastapi.testclient import TestClient

from app.conf import ConfigurationContainer, cloud_provider_additional_environment
from app.auth.auth import require_opendes_authorized_user
from app.middleware.basic_context_middleware import require_data_partition_id
from app.clients import SearchServiceClient, StorageRecordServiceClient, make_storage_record_client
from app.helper.traces import CombinedExporter
from app.injector.app_injector import WithLifeTime
from app.base import base_app
from app.wdms_app import wdms_app, app_injector
from app.routers.bulk.utils import set_welllog_data_consistency_check, set_trajectory_data_consistency_check
from app.bulk_persistence import BulkPersistenceConfig
from app.bulk_persistence import DaskBulkStorage
from app.bulk_persistence import SessionsStorage
from osdu.core.api.storage.blob_storage_base import BlobStorageBase


@pytest.fixture(scope="module")
def local_bulk_persistence_config(local_dev_config):
    """
    Creates a new instance of BulkPersistenceConfig with default inits
    """
    bulk_config = BulkPersistenceConfig(
        min_worker_memory=local_dev_config.min_worker_memory.value,
        dask_data_ipc=local_dev_config.dask_data_ipc.value,
        service_name=local_dev_config.service_name.value
    )

    yield bulk_config


@pytest.fixture(scope="module")
def local_dev_config(tmp_path_factory):
    config = ConfigurationContainer.with_load_all(environment_dict={
        # set config to a local dev config (assumption for running unit tests)
        "OS_WELLBORE_DDMS_DEV_MODE": "True",
        "CLOUD_PROVIDER": "local",
        "SERVICE_HOST_STORAGE": "https://test-endpoint/api/storage",
        "SERVICE_HOST_SEARCH": "https://test-endpoint/api/search",
        "MODULES": "log_recognition.routers.log_recognition",
        'USE_LOCALFS_BLOB_STORAGE_WITH_PATH': str(tmp_path_factory.mktemp(basename="blob-")),
        'USE_INTERNAL_STORAGE_SERVICE_WITH_PATH': str(tmp_path_factory.mktemp(basename="storage-")),
        # This one is necessary as long as we have can_run() in modules depending on it
        "ENVIRONMENT_NAME": "evd"
    }, contextual_loader=cloud_provider_additional_environment)

    # patching Config in app.conf module, so it is found by other modules
    with mock.patch('app.conf.Config', config):
        # returning the config for explicit use in tests.
        yield config

    # mock.patch will restore original Config on exiting context, after fixture use.


@pytest.fixture
def mock_storage_client_holding_data(local_dev_config, nope_logger_fixture):
    """
    Fixture mocking the Storage Client, except for a specific record that we want to return when requested.
     The data we want the Client to hold and return as the service would normally do is passed as an argument.

     For usage examples, see fixtures_test.py in this directory

     We depend on :
     - local_dev_config to have a valid configuration, but also avoid doing unexpected network requests
     - nope_logger_fixture because configuring this will mount middlewares, and they need a logger
    """

    def setup_data_for_mock(data):
        template_client = make_storage_record_client(
            host=local_dev_config.service_host_storage.value,
            timeout=local_dev_config.de_client_config_timeout.value
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
            if attribute is not None:
                raise NotImplementedError("mocked_get_record does not support 'attribute' parameter")

            return await self.get_record_version(id, None, data_partition_id, appkey, token)

        async def mocked_get_record_version(self,
                                     id: str,
                                     version: int,
                                     data_partition_id: str = None,
                                     appkey: str = None,
                                     token: str = None) -> odes_storage.models.Record:
            """
            If version is None it will return the latest version. To determine the latest version, two cases:
              * the version field in the record is not set or None => considered as the latest
              * the version field set and not None => latest = record with the greater version (basic int comparison)
            """

            latest = None
            for d in data:
                # CAREFUL: id might be optional in the model (not set on write)
                # Also storage seems to have problematic behavior with id ending in ':'
                if id is not None and (id == d.id or id + ":" == d.id):
                    if version == d.version:
                        return d

                    if latest is None \
                       or latest.version is None \
                       or (d.version is not None and d.version > latest.version):
                        latest = d

            if latest is not None:
                return latest

            # if not found, attempt to emulate behavior of the actual client
            raise odes_storage.UnexpectedResponse(
                status_code=404,
                reason_phrase="Item not found",
                # not sure what to put here at this time
                content="".encode(encoding="utf-8"),
                headers=httpx.Headers(),
            )

        async def mocked_get_all_record_versions(self,
                                                 id: str,
                                                 data_partition_id: str) -> odes_storage.models.RecordVersions:
            versions = []
            record_found = False
            for d in data:
                # CAREFUL: id might be optional in the model (not set on write)
                # Also storage seems to have problematic behavior with id ending in ':'
                if id is not None and (id == d.id or id + ":" == d.id):
                    record_found = True
                    if d.version is not None:  # Note: version None means latest
                        versions.append(d.version)
            # if not found, attempt to emulate behavior of the actual client
            if not record_found:
                raise odes_storage.UnexpectedResponse(
                    status_code=404,
                    reason_phrase="Item not found",
                    # not sure what to put here at this time
                    content="".encode(encoding="utf-8"),
                    headers=httpx.Headers(),
                )
            return odes_storage.models.RecordVersions(recordId=id, versions=versions or None)

        # override get_record method on the instance to return sample data
        mock.get_record = types.MethodType(mocked_get_record, mock)
        mock.get_record_version = types.MethodType(mocked_get_record_version, mock)
        mock.get_all_record_versions = types.MethodType(mocked_get_all_record_versions, mock)

        return mock

    return setup_data_for_mock


@pytest.fixture(scope="module")
def base_app_initialized_with_testclient(local_dev_config, dask_client):
    """
    Fixture providing wdms_app started, along with a test client
    """

    # retrieve the dask_client starter, but let the app close it.
    # CAREFUL about the fixture scope
    with dask_client(autoclose_asynccontext=False) as dask_client_starter:

        # Mocking dask_client for app to use it
        with mock.patch('app.bulk_persistence.dask.client.DaskClient.create', dask_client_starter):

            with TestClient(base_app) as base_client:
                yield base_client

            # slb_app shutdown event should call DaskClient.close()

        # mock will return DaskClient.create to its original state
    # context will close current client


@pytest.fixture(scope="module")
def app_initialized_with_testclient(base_app_initialized_with_testclient):
    """
    Fixture providing wdms_app started, along with a test client
    """
    # dependent fixture because base_app and wdms_app are interdependent

    with TestClient(wdms_app) as client:
        yield wdms_app, client


@pytest.fixture
def app_configurable_with_testclient(app_initialized_with_testclient):
    """
    Fixture to configure wdms_app after it has been started.
    It returns a function to be called from the test to configure the app,
     and it will return the configured app, along with its client.

    By default, everything will be mocked with mock.AsyncMock() instances and an authorized opendes user.

    For example usage, check fixtures_test.py
    """

    app, client = app_initialized_with_testclient

    # saving app state for reset later on
    original_trace_exporter = app.trace_exporter
    original_dependency_overrides = copy.copy(app.dependency_overrides)

    loop = asyncio.get_event_loop()
    original_storage_client = loop.run_until_complete(app_injector.get(StorageRecordServiceClient))
    original_search_client = loop.run_until_complete(app_injector.get(SearchServiceClient))

    # setup safe defaults for tests
    default_storage_mock = AsyncMock(spec=StorageRecordServiceClient)
    # override api_client to use an async mock (needed on shutdown when we call api_client.close())
    default_storage_mock.api_client = AsyncMock()

    default_search_mock = AsyncMock(spec=SearchServiceClient)
    # override api_client to use an async mock (needed on shutdown when we call api_client.close())
    default_search_mock.api_client = AsyncMock()

    def injection_coro_builder(*, return_value):
        # because of our app_injector design
        async def injection_coro(
                *args, **kwargs
        ):
            return return_value
        return injection_coro

    def configure_app(
        *,
        search_client_mock=default_search_mock,
        storage_client_mock=default_storage_mock,
        dask_bulk_storage_mock=None,
        blob_storage_base_mock=None,
        sessions_storage_mock=None,
        trace_exporter=create_autospec(CombinedExporter, spec_set=True, instance=True),
        fake_opendes_authorized_user: bool = True,
        fake_data_partition_id: bool = False,
        disable_bulk_consistency: bool = False,
    ):
        """builder generator that output an app mocked by default, and cleanup properly after use.
        If None is passed as a mock, then the original implementation is used.
        """
        nonlocal app, client

        ## configure app_injector -- needs to be reset after fixture execution ##
        if storage_client_mock is not None:
            app_injector.register(
                StorageRecordServiceClient, injection_coro_builder(return_value=storage_client_mock),
        WithLifeTime.Singleton()
            )

        if search_client_mock is not None:
            app_injector.register(SearchServiceClient, injection_coro_builder(return_value=search_client_mock),
        WithLifeTime.Singleton())

        if dask_bulk_storage_mock is not None:
            app_injector.register(DaskBulkStorage, injection_coro_builder(return_value=dask_bulk_storage_mock))

        if blob_storage_base_mock is not None:
            app_injector.register(BlobStorageBase, injection_coro_builder(return_value=blob_storage_base_mock))

        if sessions_storage_mock is not None:
            app_injector.register(SessionsStorage, injection_coro_builder(return_value=sessions_storage_mock))


        ## configure app -- needs to be reset after fixture execution ##
        app.trace_exporter = trace_exporter

        async def opendes_authorized_user_mock_depend():
            pass

        app.dependency_overrides[
            require_opendes_authorized_user
        ] = opendes_authorized_user_mock_depend if fake_opendes_authorized_user else require_opendes_authorized_user

        async def require_data_partition_id_mock_depend():
            pass

        app.dependency_overrides[
            require_data_partition_id
        ] = require_data_partition_id_mock_depend if fake_data_partition_id else require_data_partition_id

        if disable_bulk_consistency:
            app.dependency_overrides[set_welllog_data_consistency_check] = lambda: None
            app.dependency_overrides[set_trajectory_data_consistency_check] = lambda: None

        # return the app, ready to be started along with the client
        return app, client

    yield configure_app

    # reset app for reuse (we always cleanup without recreating the app - it would be too slow)
    app_injector.register(
                StorageRecordServiceClient, injection_coro_builder(return_value=original_storage_client),
        WithLifeTime.Singleton())
    app_injector.register(
                SearchServiceClient, injection_coro_builder(return_value=original_search_client),
        WithLifeTime.Singleton())

    app.trace_exporter = original_trace_exporter

    app.dependency_overrides = original_dependency_overrides

