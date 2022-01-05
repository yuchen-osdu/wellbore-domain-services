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
from tempfile import TemporaryDirectory

import pytest
import mock
import json
import os

from fastapi.testclient import TestClient

from fastapi import Header, status

from odes_storage.models import CreateUpdateRecordsResponse, Record, RecordVersions
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from starlette.responses import Response

import pandas as pd

from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage, make_local_dask_bulk_storage
from app.model.model_chunking import GetDataParams
from app.model.osdu_model import Wellbore, Well, WellLog, WellboreTrajectory, WellboreMarkerSet
from app.clients import SearchServiceClient, StorageRecordServiceClient

from app.helper import traces
from app.middleware import require_data_partition_id
from app.auth.auth import require_opendes_authorized_user
from app.persistence.sessions_storage import SessionsStorage
from app.routers.bulk.utils import DataFrameRender
from app.utils import Context
from app.wdms_app import wdms_app, app_injector
from tests.unit.persistence.dask_blob_storage_test import generate_df
from tests.unit.test_utils import create_mock_class, nope_logger_fixture

"""
Contains unified common tests for the different kind. Mainly CRUD test cases
"""

tests_parameters = [
    (
        "/ddms/v3/wellbores",
        r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
        Wellbore(
            id=r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:",
            kind="namespace:osdu:master-data--Wellbore:1.0.0",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        ),
    ),
    (
        "/ddms/v3/wellbores",
        r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
        Wellbore(
            id=r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9:145",
            kind="namespace:osdu:master-data--Wellbore:1.0.0",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        ),
    ),
]

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def client(nope_logger_fixture):
    async def bypass_authorization():
        # empty method
        pass

    with TemporaryDirectory() as tmp_dir:
        local_blob_storage = LocalFSBlobStorage(directory=tmp_dir)

        async def set_default_partition(data_partition_id: str = Header("opendes")):
            Context.set_current_with_value(partition_id=data_partition_id)

        async def build_mock_storage():
            return StorageRecordServiceClientMock()

        async def build_mock_search():
            return SearchServiceClientMock()

        async def blob_storage_builder(*args, **kwargs):
            return local_blob_storage

        async def sessions_storage_builder(*args, **kwargs):
            return SessionsStorage(local_blob_storage)

        async def dask_blob_storage_builder() -> DaskBulkStorage:
            return await make_local_dask_bulk_storage(base_directory=tmp_dir)

        app_injector.register(DaskBulkStorage, dask_blob_storage_builder)
        app_injector.register(BlobStorageBase, blob_storage_builder)
        app_injector.register(SessionsStorage, sessions_storage_builder)
        app_injector.register(StorageRecordServiceClient, build_mock_storage)
        app_injector.register(SearchServiceClient, build_mock_search)

        # override authentication dependency
        previous_overrides = wdms_app.dependency_overrides

        try:
            wdms_app.dependency_overrides[
                require_opendes_authorized_user
            ] = bypass_authorization
            wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
            client = TestClient(wdms_app)
            yield client
        finally:
            wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")


def test_post_records_successful(client):
    base_url = "/ddms/v3/wellbores"
    expected_response = CreateUpdateRecordsResponse(
        recordCount=1,
        recordIds=[
            r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9"
        ],
    )

    moc_create_or_update_records = mock.AsyncMock(return_value=expected_response)

    with mock.patch.object(
            StorageRecordServiceClientMock,
            "create_or_update_records",
            moc_create_or_update_records,
    ):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, r"Wellbore_unit.json")) as f:
            test_Wellbores = json.load(f)
        Wellbore.parse_obj(test_Wellbores[0])
        # when
        response = client.post(base_url, data=json.dumps(test_Wellbores), headers={'content-type': 'application/json'})

        # then
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


getas_parameters = [
    (Wellbore, "/ddms/v3/wellbores", r"../../converter/wellbore_wks.json", "opendes:wellbore:12345",
     status.HTTP_400_BAD_REQUEST),
    (Wellbore, "/ddms/v3/wellbores", r"../../converter/wellbore_wks.json",
     "opendes:master-data--Wellbore:6f70656e6465733a646f633a3132333435:", status.HTTP_422_UNPROCESSABLE_ENTITY),
    (Well, "/ddms/v3/wells", r"../../converter/well_wks.json", "opendes:well:12345",
     status.HTTP_400_BAD_REQUEST),
    (Well, "/ddms/v3/wells", r"../../converter/well_wks.json",
     "opendes:master-data--Well:6f70656e6465733a646f633a3132333435:", status.HTTP_422_UNPROCESSABLE_ENTITY),
]


def replace_template(source_obj_str: str) -> str:
    source_obj_str = source_obj_str.replace("{{datapartitionid}}", "datapartitionid") \
        .replace("{datapartitionid}", "datapartitionid").replace("{{domain}}", "domain") \
        .replace("{{wellboreId}}", "wellboreId").replace("{{wellId}}", "wellId")
    return source_obj_str


@pytest.mark.parametrize("entity_class, base_url, source_file, record_id, expected_response", getas_parameters)
def test_get_record_as_OSDU(client, entity_class, base_url, source_file, record_id, expected_response):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, source_file)) as f:
        record_str = replace_template(f.read())
        source_record = json.loads(record_str)
    if isinstance(source_record, list):
        source_record = source_record[0]
    record_entity = Record.parse_obj(source_record)
    moc = mock.AsyncMock(return_value=record_entity)

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc):

        # when
        response = client.get(
            f"{base_url}/{record_id}",
            headers={"data-partition-id": "testing_partition"},
        )

        assert response.status_code == expected_response
        if response.status_code == status.HTTP_200_OK:
            # assert it validates the input object schema
            res = response.json()
            entity_class.validate(res)


get_invalid_id_parameters = [
    (Wellbore, "/ddms/v3/wellbores", "toto"),
    (Well, "/ddms/v3/wells", "schmurf"),
]


@pytest.mark.parametrize("entity_class, base_url, record_id", get_invalid_id_parameters)
def test_get_record_incorrect_id(client, entity_class, base_url, record_id):
    response = client.get(
        f"{base_url}/{record_id}",
        headers={"data-partition-id": "testing_partition"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("base_url, id, record_obj", tests_parameters)
def test_get_record_success(client, base_url, id, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc):
        # when
        response = client.get(
            f"{base_url}/{record_id}",
            headers={"data-partition-id": "testing_partition"},
        )
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=id, data_partition_id="testing_partition")

        # assert it validates the input object schema
        record_obj.validate(response.json())


tests_parameters_restricted_record_id = [
    (
        "/ddms/v3/wells",
        r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9"
    ),
    (
        "/ddms/v3/wellbores",
        r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32qwer9"
    ),
    (
        "/ddms/v3/welllogs",
        r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9"
    ),
    (
        "/ddms/v3/wellboretrajectories",
        r"namespace:work-product-component--WellboreTrajectory:c7c421a7-f496-5aef-8093-298c32bfdea9"
    ),
    (
        "/ddms/v3/wellboremarkersets",
        r"namespace:work-product-component--WellboreMarkerSet:c7c421a7-f496-5aef-8093-298c32bfdea9"
    )
]

tests_parameters_restricted_well = [
    (
        r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9",
        {
            "id": "namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9:",
            "kind": "namespace:osdu:master-data--Well:1.0.0",
            "acl": {"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            "legal": {"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
            "data": {}
        },
        Well(
            id=r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9:",
            kind="namespace:osdu:master-data--Well:1.0.0",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            version=1976,
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        )
    )]


def validation_test_restricted_record_id(record_id, record_id_to_test, response, ok_response=status.HTTP_200_OK,
                                         error_response=status.HTTP_400_BAD_REQUEST):
    if record_id != record_id_to_test:
        assert response.status_code == error_response
    else:
        assert response.status_code == ok_response


@pytest.mark.parametrize("base_url, id", tests_parameters_restricted_record_id)
@pytest.mark.parametrize("id_to_test, record_to_test, record_obj_to_test", tests_parameters_restricted_well)
def test_restricted_record_id(client, base_url, id, id_to_test, record_to_test, record_obj_to_test):
    record_id = id
    record_id_to_test = id_to_test
    version = 65469556549465
    chunk = pd.DataFrame([[10, 11]], index=[1], columns=['c1', 'c2'])
    version_obj = RecordVersions(recordId=record_id_to_test, versions=[version])
    create_update_records_obj = CreateUpdateRecordsResponse(record_count=1, record_ids=["1"], skipped_record_ids=["1"])
    moc_get_record = mock.AsyncMock(return_value=record_obj_to_test)
    moc_get_all_record_versions = mock.AsyncMock(return_value=version_obj)
    moc_create_or_update_records = mock.AsyncMock(return_value=create_update_records_obj)
    moc_delete_records = mock.AsyncMock(return_value=Response())

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc_get_record), \
         mock.patch.object(StorageRecordServiceClientMock, "get_record_version", moc_get_record), \
         mock.patch.object(StorageRecordServiceClientMock, "get_all_record_versions", moc_get_all_record_versions), \
         mock.patch.object(StorageRecordServiceClientMock, "create_or_update_records", moc_create_or_update_records), \
         mock.patch("app.routers.bulk.bulk_routes.set_bulk_field_and_send_record", moc_create_or_update_records), \
         mock.patch.object(StorageRecordServiceClientMock, "delete_record", moc_delete_records):
        response = client.post(f"{base_url}", json=[record_to_test])

        validation_test_restricted_record_id(record_id, record_id_to_test, response,
                                             error_response=status.HTTP_422_UNPROCESSABLE_ENTITY)

        response = client.get(f"{base_url}/{record_id_to_test}")
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        response = client.get(f"{base_url}/{record_id_to_test}/versions")
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        response = client.get(f'{base_url}/{record_id_to_test}/versions/{version}')
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        if base_url == "/ddms/v3/welllogs" or base_url == "/ddms/v3/wellboretrajectories":
            # Session
            response = client.post(f'{base_url}/{record_id_to_test}/sessions',
                                   json={"fromVersion": 11351351, 'mode': 'update'})
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            session_id = "56df654df654df65"
            response = client.post(f'{base_url}/{record_id_to_test}/sessions/{session_id}/data',
                                   data=chunk.to_json(orient='split'),
                                   headers={'Content-Type': 'application/json'})
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            response = client.get(f'{base_url}/{record_id_to_test}/sessions')
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            response = client.get(f'{base_url}/{record_id_to_test}/sessions/{session_id}')
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            # Data
            moc_record = Record(
                id=r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9:",
                kind="namespace:osdu:master-data--Well:1.0.0",
                acl={"owners": ["test"], "viewers": ["test"]},
                version=1976,
                legal={"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
                data={'name': 'myWell', 'uwi': '00-000-00000-00', 'ExtensionProperties': {
                    'wdms': {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81'}}},
            )
            with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                                   mock.AsyncMock(return_value=moc_record)), \
                 mock.patch("app.bulk_persistence.dask.dask_bulk_storage.DaskBulkStorage.save_blob",
                            mock.AsyncMock(return_value=0)):
                data = '{"columns": ["Ref"], "index": [0], "data": [[0]]}'
                headers = {'content-type': 'application/json'}

                response = client.post(f'{base_url}/{record_id_to_test}/data', data=data, headers=headers)
                validation_test_restricted_record_id(record_id, record_id_to_test, response)

                response = client.get(f'{base_url}/{record_id_to_test}/data?orient=split',
                                      headers={'Accept': 'application/json'})
                validation_test_restricted_record_id(record_id, record_id_to_test, response)

                response = client.get(f'{base_url}/{record_id_to_test}/versions/{version}/data')
                validation_test_restricted_record_id(record_id, record_id_to_test, response)


tests_parameters_record_ids = [
    (
        "/ddms/v3/welllogs",
        r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9",
        "namespace:osdu:work-product-component--WellLog:1.0.0"
    ),
    (
        "/ddms/v3/wellboretrajectories",
        r"namespace:work-product-component--WellboreTrajectory:c7c421a7-f496-5aef-8093-298c32bfdea9",
        "namespace:osdu:work-product-component--WellboreTrajectory:1.0.0"
    )
]

def records_for_invalid_bulk_uri_set_test(record_id, record_kind, data):
    record_to_test = {
    "id": record_id,
    "kind": record_kind,
    "acl": {"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
    "legal": {"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
    "data": data
    }
    return record_to_test

@pytest.mark.parametrize("base_url, record_id, record_kind", tests_parameters_record_ids)
def test_invalid_bulk_uri_set(client, base_url, record_id, record_kind):
    data = {}
    chunk = pd.DataFrame([[10, 11]], index=[1], columns=['c1', 'c2'])
    create_update_records_obj = CreateUpdateRecordsResponse(record_count=1, record_ids=["1"], skipped_record_ids=["1"])
    moc_get_record = mock.AsyncMock(return_value=record_id)
    moc_create_or_update_records = mock.AsyncMock(return_value=create_update_records_obj)
    moc_delete_records = mock.AsyncMock(return_value=Response())

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc_get_record), \
         mock.patch.object(StorageRecordServiceClientMock, "create_or_update_records", moc_create_or_update_records), \
         mock.patch("app.routers.bulk.bulk_routes.set_bulk_field_and_send_record", moc_create_or_update_records), \
         mock.patch.object(StorageRecordServiceClientMock, "delete_record", moc_delete_records):
        # response = client.get(f"{base_url}/{record_id_to_test}")

        record_to_test = records_for_invalid_bulk_uri_set_test(record_id=record_id, record_kind=record_kind, data=data)
        response = client.post(f"{base_url}", json=[record_to_test])
        assert response.status_code == status.HTTP_200_OK

        record_to_test = records_for_invalid_bulk_uri_set_test(record_id=None, record_kind=record_kind, data={})
        response = client.post(f"{base_url}", json=[record_to_test])
        assert response.status_code == status.HTTP_200_OK

        data = {"ExtensionProperties": {"wdms": {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236cca00'}}}
        record_to_test = records_for_invalid_bulk_uri_set_test(record_id=record_id, record_kind=record_kind, data=data)
        response = client.post(f"{base_url}", json=[record_to_test])
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        record_to_test = records_for_invalid_bulk_uri_set_test(record_id=None, record_kind=record_kind, data=data)
        response = client.post(f"{base_url}", json=[record_to_test])
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Data
        moc_record = Record(
            id=record_id,
            kind=record_kind,
            acl={"owners": ["test"], "viewers": ["test"]},
            version=1976,
            legal={"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
            data={'name': 'myWell', 'uwi': '00-000-00000-00', 'ExtensionProperties': {
                'wdms': {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81'}}},
        )
        with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                               mock.AsyncMock(return_value=moc_record)), \
             mock.patch("app.bulk_persistence.dask.dask_bulk_storage.DaskBulkStorage.save_blob",
                        mock.AsyncMock(return_value=0)):
            record_to_test = records_for_invalid_bulk_uri_set_test(record_id=record_id, record_kind=record_kind, data=data)
            response = client.post(f"{base_url}", json=[record_to_test])
            assert response.status_code == status.HTTP_400_BAD_REQUEST

            data = {"ExtensionProperties": {"wdms": {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81'}}}
            record_to_test = records_for_invalid_bulk_uri_set_test(record_id=record_id, record_kind=record_kind, data=data)
            response = client.post(f"{base_url}", json=[record_to_test])
            assert response.status_code == status.HTTP_200_OK