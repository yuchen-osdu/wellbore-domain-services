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

import asyncio
import copy
import os
import pytest
from unittest.mock import create_autospec, patch
import uuid

import pandas as pd
from pandas.util.testing import assert_frame_equal

from odes_storage.models import CreateUpdateRecordsResponse, Record

from app.clients.storage_service_client import StorageRecordServiceClient
from app.helper import traces
from app.routers.ddms_v2.log_ddms_v2 import (
    _get_log_data,
    _write_log_data,
    get_persistence,
)
from app.routers.record_utils import fetch_record, update_records
from app import wdms_app

from tests.unit.test_utils import ctx_fixture

data_partition_id = 'test_partition'

log_payload = {
    "acl": {
        "owners": [
            "data.default.owners@opendes.p4d.cloud.slb-ds.com"
        ],
        "viewers": [
            "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
        ]
    },
    "legal": {
        "legaltags": [
            "opendes-public-usa-dataset-1"
        ],
        "otherRelevantDataCountries": ["US", "FR"],
        "status": None
    },
    "kind": f"{data_partition_id}:wks:log:1.0.5",
    "data": {
        "name": f"{os.path.basename(__file__)}"
    }
}


storage_record_service_client_mock = create_autospec(StorageRecordServiceClient, spec_set=True, instance=True)


@pytest.fixture
async def ctx_with_test_setup(app_configurable_with_testclient, ctx_fixture):
    # app_configurable_with_testclient may be  overkill (for instance we do not need dask cluster, neither TestClient)
    # and might slower the test setup
    # but it avoids copy/paste and it works well and cleanup correctly at teardown.
    app_configurable_with_testclient(
        storage_client_mock=storage_record_service_client_mock,
    )

    # Usually basic_context_middleware sets the app injector in the context
    # but since those tests call directly internal function instead making call to  apis
    # the app injector is not set in the context whereas functions under test need it for retrieving storage service client.
    # so we have to set manually the app injector in the context.
    ctx = ctx_fixture.set_current_with_value(partition_id=data_partition_id, app_injector=wdms_app.app_injector)

    return ctx


@pytest.fixture
def mock_persistence():
    class MockPersistence:

        def __init__(self):
            self.dataframe = None
            self.id = None

        async def read_bulk(self, ctx, record: Record, bulk_id_path: str) -> pd.DataFrame:
            return self.dataframe

        async def write_bulk(self, ctx, dataframe) -> str:
            self.dataframe = dataframe
            self.id = str(uuid.uuid4())
            return self.id

    mock = MockPersistence()

    async def override_get_persistence():
        return mock

    previous_overrides = copy.copy(wdms_app.dependency_overrides)

    wdms_app.dependency_overrides[get_persistence] = override_get_persistence
    yield mock

    wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.mark.anyio
async def test_fetch_record(ctx_with_test_setup):
    expected_record = Record.parse_obj(log_payload)
    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as moc_get_record, \
            patch.object(storage_record_service_client_mock, 'get_record_version',
                         return_value=expected_record) as moc_get_record_version:
        computed_record = await fetch_record(ctx_with_test_setup, record_id="132")

        assert computed_record == expected_record
        moc_get_record.assert_called_with(id="132", data_partition_id=data_partition_id, attribute=None)
        moc_get_record_version.assert_not_called()


@pytest.mark.anyio
async def test_fetch_record_version(ctx_with_test_setup):

    expected_record = Record.parse_obj(log_payload)

    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as moc_get_record,\
         patch.object(storage_record_service_client_mock, 'get_record_version',
                      return_value=expected_record) as moc_get_record_version:

        computed_record = await fetch_record(ctx_with_test_setup, record_id="132", version="1")

        assert computed_record == expected_record
        moc_get_record_version.assert_called_with(id="132", data_partition_id=data_partition_id, version="1",
                                                  attribute=None)
        moc_get_record.assert_not_called()


@pytest.mark.anyio
async def test_update_records(ctx_with_test_setup):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])

    with patch.object(storage_record_service_client_mock, 'create_or_update_records',
                      return_value=expected_response) as moc:
        record = Record.parse_obj(log_payload)
        computed_response = await update_records(ctx_with_test_setup, records=[record])

        assert computed_response == expected_response
        moc.assert_called_with(record=[record], data_partition_id=data_partition_id)


@pytest.mark.anyio
async def test_write_log_data(ctx_with_test_setup, mock_persistence):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])
    expected_record = Record.parse_obj(log_payload)

    data = pd.DataFrame.from_dict({'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']})

    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as get_record_moc,\
         patch.object(storage_record_service_client_mock, 'create_or_update_records',
                      return_value=expected_response) as create_or_update_records_moc:

        computed_response = await _write_log_data(
            ctx_with_test_setup,
            persistence=mock_persistence,
            logid="1234",
            bulk_path=None,
            dataframe=data)

        assert computed_response == expected_response
        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id, attribute=None)
        create_or_update_records_moc.assert_called_once_with(record=[expected_record],
                                                             data_partition_id=data_partition_id)
        assert_frame_equal(mock_persistence.dataframe, data)


@pytest.mark.anyio
async def test_write_log_data_with_bulk_path(ctx_with_test_setup, mock_persistence):
    expected_response = CreateUpdateRecordsResponse(record_count=2, record_ids=["1", "2"], skipped_record_ids=["1"])

    expected_record = Record.parse_obj(log_payload)
    expected_record.data["custom_bulkid"] = "default"

    data = pd.DataFrame.from_dict({'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']})

    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as get_record_moc,\
         patch.object(storage_record_service_client_mock, 'create_or_update_records',
                      return_value=expected_response) as create_or_update_records_moc:
        computed_response = await _write_log_data(
            ctx_with_test_setup,
            persistence=mock_persistence,
            logid="1234",
            bulk_path="data.custom_bulkid",
            dataframe=data)

        assert computed_response == expected_response
        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id, attribute=None)
        create_or_update_records_moc.assert_called_once_with(record=[expected_record],
                                                             data_partition_id=data_partition_id)
        assert_frame_equal(mock_persistence.dataframe, data)


@pytest.mark.anyio
async def test_get_log_data(ctx_with_test_setup, mock_persistence):
    expected_record = Record.parse_obj(log_payload)
    expected_data = {'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']}

    mock_persistence.dataframe = pd.DataFrame.from_dict(expected_data)

    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as get_record_moc:

        computed_response = await _get_log_data(
            ctx_with_test_setup,
            persistence=mock_persistence,
            logid="1234",
            version=None,
            orient="columns",
            bulk_id_path=None)

        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id, attribute=None)

        assert computed_response.status_code == 200
        assert computed_response.body == b'{"col_1":{"0":3,"1":2,"2":1,"3":0},"col_2":{"0":"a","1":"b","2":"c","3":"d"}}'
        assert computed_response.media_type == 'application/json'


@pytest.mark.anyio
async def test_get_log_data_with_bulk_path(ctx_with_test_setup, mock_persistence):
    expected_record = Record.parse_obj(log_payload)
    expected_record.data["custom_bulkid"] = "424242"
    expected_data = {'col_1': [3, 2, 1, 0], 'col_2': ['a', 'b', 'c', 'd']}

    mock_persistence.dataframe = pd.DataFrame.from_dict(expected_data)

    with patch.object(storage_record_service_client_mock, 'get_record',
                      return_value=expected_record) as get_record_moc:

        computed_response = await _get_log_data(
            ctx_with_test_setup,
            persistence=mock_persistence,
            logid="1234",
            version=None,
            orient="columns",
            bulk_id_path="data.custom_bulkid")

        get_record_moc.assert_called_once_with(id="1234", data_partition_id=data_partition_id, attribute=None)

        assert computed_response.status_code == 200
        assert computed_response.body == b'{"col_1":{"0":3,"1":2,"2":1,"3":0},"col_2":{"0":"a","1":"b","2":"c","3":"d"}}'
        assert computed_response.media_type == 'application/json'


