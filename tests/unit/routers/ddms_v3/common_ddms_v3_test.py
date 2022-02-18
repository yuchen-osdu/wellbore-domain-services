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
import os
import mock
from odes_storage import UnexpectedResponse
import pandas as pd
import pytest
from app.auth.auth import require_opendes_authorized_user
from app.bulk_persistence.dask.dask_bulk_storage import DaskBulkStorage
from app.bulk_persistence.dask.dask_bulk_storage_local import make_local_dask_bulk_storage
from app.clients import SearchServiceClient, StorageRecordServiceClient
from app.helper import traces
from app.middleware import require_data_partition_id
from app.model.osdu_model import Well, Wellbore
from app.persistence.sessions_storage import SessionsStorage
from app.wdms_app import app_injector, wdms_app
from fastapi import status
from fastapi.testclient import TestClient
from odes_storage.models import CreateUpdateRecordsResponse, Record, RecordVersions
from osdu.core.api.storage.blob_storage_base import BlobStorageBase
from osdu.core.api.storage.blob_storage_local_fs import LocalFSBlobStorage
from starlette.responses import Response
from tests.unit.conftest import do_nothing, set_default_partition
from tests.unit.test_utils import create_mock_class


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
def dasked_test_app_with_mocked_core_service(event_loop, tmp_path):
    local_blob_storage = LocalFSBlobStorage(directory=str(tmp_path))

    async def build_mock_storage():
        return StorageRecordServiceClientMock()

    async def build_mock_search():
        return SearchServiceClientMock()

    async def blob_storage_builder(*args, **kwargs):
        return local_blob_storage

    async def sessions_storage_builder(*args, **kwargs):
        return SessionsStorage(local_blob_storage)

    async def dask_blob_storage_builder() -> DaskBulkStorage:
        return await make_local_dask_bulk_storage(base_directory=str(tmp_path))

    app_injector.register(DaskBulkStorage, dask_blob_storage_builder)
    app_injector.register(BlobStorageBase, blob_storage_builder)
    app_injector.register(SessionsStorage, sessions_storage_builder)
    app_injector.register(StorageRecordServiceClient, build_mock_storage)
    app_injector.register(SearchServiceClient, build_mock_search)

    # override authentication dependency
    previous_overrides = wdms_app.dependency_overrides

    try:
        wdms_app.dependency_overrides[require_opendes_authorized_user] = do_nothing
        wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
        client = TestClient(wdms_app)
        yield client
    finally:
        wdms_app.dependency_overrides = previous_overrides  # clean up


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name="tested-ddms")


def test_post_records_successful(dasked_test_app_with_mocked_core_service):
    base_url = "/ddms/v3/wellbores"
    expected_response = CreateUpdateRecordsResponse(
        recordCount=1,
        recordIds=[r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9"],
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
        response = dasked_test_app_with_mocked_core_service.post(
            base_url, data=json.dumps(test_Wellbores), headers={"content-type": "application/json"}
        )

        # then
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


def replace_template(source_obj_str: str) -> str:
    source_obj_str = (
        source_obj_str.replace("{{datapartitionid}}", "datapartitionid")
            .replace("{datapartitionid}", "datapartitionid")
            .replace("{{domain}}", "domain")
            .replace("{{wellboreId}}", "wellboreId")
            .replace("{{wellId}}", "wellId")
    )
    return source_obj_str


get_invalid_id_parameters = [
    (Wellbore, "/ddms/v3/wellbores", "toto"),
    (Well, "/ddms/v3/wells", "schmurf"),
]


@pytest.mark.parametrize("entity_class, base_url, record_id", get_invalid_id_parameters)
def test_get_record_incorrect_id(dasked_test_app_with_mocked_core_service, entity_class, base_url, record_id):
    response = dasked_test_app_with_mocked_core_service.get(
        f"{base_url}/{record_id}",
        headers={"data-partition-id": "testing_partition"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize("base_url, id, record_obj", tests_parameters)
def test_get_record_success(dasked_test_app_with_mocked_core_service, base_url, id, record_obj):
    record_id = record_obj.id
    moc = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc):
        # when
        response = dasked_test_app_with_mocked_core_service.get(
            f"{base_url}/{record_id}",
            headers={"data-partition-id": "testing_partition"},
        )
        assert response.status_code == status.HTTP_200_OK

        # then assert storage is called with the proper id and data_partition
        moc.assert_called_with(id=id, data_partition_id="testing_partition")

        # assert it validates the input object schema
        record_obj.validate(response.json())


tests_parameters_restricted_record_id = [
    ("/ddms/v3/wells", r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9"),
    ("/ddms/v3/wellbores", r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32qwer9"),
    ("/ddms/v3/welllogs", r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9"),
    (
        "/ddms/v3/wellboretrajectories",
        r"namespace:work-product-component--WellboreTrajectory:c7c421a7-f496-5aef-8093-298c32bfdea9",
    ),
    (
        "/ddms/v3/wellboremarkersets",
        r"namespace:work-product-component--WellboreMarkerSet:c7c421a7-f496-5aef-8093-298c32bfdea9",
    ),
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
    )
]


def validation_test_restricted_record_id(
        record_id, record_id_to_test, response, ok_response=status.HTTP_200_OK,
        error_response=status.HTTP_400_BAD_REQUEST
):
    if record_id != record_id_to_test:
        assert response.status_code == error_response
    else:
        assert response.status_code == ok_response


@pytest.mark.parametrize("base_url, id", tests_parameters_restricted_record_id)
@pytest.mark.parametrize("id_to_test, record_to_test, record_obj_to_test", tests_parameters_restricted_well)
def test_restricted_record_id(
        dasked_test_app_with_mocked_core_service, base_url, id, id_to_test, record_to_test, record_obj_to_test
):
    record_id = id
    record_id_to_test = id_to_test
    version = 65469556549465
    chunk = pd.DataFrame([[10, 11]], index=[1], columns=["c1", "c2"])
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
        response = dasked_test_app_with_mocked_core_service.post(f"{base_url}", json=[record_to_test])

        validation_test_restricted_record_id(record_id, record_id_to_test, response,
                                             error_response=status.HTTP_422_UNPROCESSABLE_ENTITY)

        response = dasked_test_app_with_mocked_core_service.get(f"{base_url}/{record_id_to_test}")
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        response = dasked_test_app_with_mocked_core_service.get(f"{base_url}/{record_id_to_test}/versions")
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        response = dasked_test_app_with_mocked_core_service.get(f"{base_url}/{record_id_to_test}/versions/{version}")
        validation_test_restricted_record_id(record_id, record_id_to_test, response)

        if base_url == "/ddms/v3/welllogs" or base_url == "/ddms/v3/wellboretrajectories":
            # Session
            response = dasked_test_app_with_mocked_core_service.post(
                f"{base_url}/{record_id_to_test}/sessions", json={"fromVersion": 11351351, "mode": "update"}
            )
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            session_id = "56df654df654df65"
            response = dasked_test_app_with_mocked_core_service.post(
                f"{base_url}/{record_id_to_test}/sessions/{session_id}/data",
                data=chunk.to_json(orient="split"),
                headers={"Content-Type": "application/json"},
            )
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            response = dasked_test_app_with_mocked_core_service.get(f"{base_url}/{record_id_to_test}/sessions")
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            response = dasked_test_app_with_mocked_core_service.get(
                f"{base_url}/{record_id_to_test}/sessions/{session_id}"
            )
            validation_test_restricted_record_id(record_id, record_id_to_test, response)

            # Data
            moc_record = Record(
                id=r"namespace:master-data--Well:c7c421a7-f496-5aef-8093-298c32gtrfd9:",
                kind="namespace:osdu:master-data--Well:1.0.0",
                acl={"owners": ["test"], "viewers": ["test"]},
                version=1976,
                legal={"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
                data={
                    "name": "myWell",
                    "uwi": "00-000-00000-00",
                    "ExtensionProperties": {
                        "wdms": {"bulkURI": "urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81"}
                    },
                },
            )
            with mock.patch.object(
                    StorageRecordServiceClientMock, "get_record", mock.AsyncMock(return_value=moc_record)
            ):
                data = '{"columns": ["Ref"], "index": [0], "data": [[0]]}'
                headers = {"content-type": "application/json"}

                response = dasked_test_app_with_mocked_core_service.post(
                    f"{base_url}/{record_id_to_test}/data", data=data, headers=headers
                )
                validation_test_restricted_record_id(record_id, record_id_to_test, response)

                response = dasked_test_app_with_mocked_core_service.get(
                    f"{base_url}/{record_id_to_test}/data?orient=split", headers={"Accept": "application/json"}
                )
                validation_test_restricted_record_id(record_id, record_id_to_test, response)

                response = dasked_test_app_with_mocked_core_service.get(
                    f"{base_url}/{record_id_to_test}/versions/{version}/data"
                )
                validation_test_restricted_record_id(record_id, record_id_to_test, response)


tests_parameters_record_ids = [
    (
        "/ddms/v3/welllogs",
        r"namespace:work-product-component--WellLog:c7c421a7-f496-5aef-8093-298c32bfdea9",
        "namespace:osdu:work-product-component--WellLog:1.0.0",
        {}
    ),
    (
        "/ddms/v3/wellboretrajectories",
        r"namespace:work-product-component--WellboreTrajectory:c7c421a7-f496-5aef-8093-298c32bfdea9",
        "namespace:osdu:work-product-component--WellboreTrajectory:1.0.0",
        {
            "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
            "TopDepthMeasuredDepth": 12345.6,
            "BaseDepthMeasuredDepth": 12345.6,
            "VerticalMeasurement": {"VerticalMeasurement": 12345.6}
        }
    )
]


def _records_for_invalid_bulk_uri_set_test(record_id, record_kind, data):
    record_to_test = {
        "id": record_id,
        "kind": record_kind,
        "acl": {"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
        "legal": {"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
        "data": data
    }
    return record_to_test


def _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url, record_id,
                                                record_kind, data, response_details):
    record_to_test = _records_for_invalid_bulk_uri_set_test(record_id=record_id, record_kind=record_kind, data=data)
    response = dasked_test_app_with_mocked_core_service.post(f"{base_url}", json=[record_to_test])
    assert response.status_code == response_details["code"]
    if response_details["message"]:
        assert response.text == response_details["message"]


def _moc_get_record_previous_version(data, record_id, record_kind):
    return Record(
        id=record_id,
        kind=record_kind,
        acl={"owners": ["test"], "viewers": ["test"]},
        version=1976,
        legal={"legaltags": ["string"], "otherRelevantDataCountries": ["FR"]},
        data=data,
    )


@pytest.mark.parametrize("base_url, record_id, record_kind, data", tests_parameters_record_ids)
def test_invalid_bulk_uri_set(dasked_test_app_with_mocked_core_service, base_url, record_id, record_kind, data):
    """
        record : Record which is tried to be created or updated gave in entry
        record_id : Record's id of the given record
        bulk_uri : Record's Bulk URI of the given record
        old_record : If "record" has a record_id, old_record is the previous version of this record
        old_bulk_uri : Previous version record's Bulk URI

        Test cases:
            With mock returning NO previous version record:
                If record has NO Bulk URI:
                    * NO Bulk URI + NO record_id :                                        200 create
                    * NO Bulk URI + record_id + NO old_record :                           200 create
                If record has Bulk URI:
                    * Bulk URI + NO record_id :                                        400 Err
                    * Bulk URI + record_id + NO old_record :                           400 Err

            With mock returning previous version record with bulk URI:
                If record has NO Bulk URI:
                    * NO Bulk URI + record_id + old_record + old_bulk_uri:             400 Err
                If record has Bulk URI:
                    * Bulk URI + record_id + old_record + old_bulk_uri + NO matching Bulk URI:             400 Err
                    * Bulk URI + record_id + old_record + old_bulk_uri + matching Bulk URI:                200 update

             With mock returning previous version record without bulk URI:
                If record has Bulk URI:
                    * Bulk URI + record_id + old_record + NO old_bulk_uri:              400 Err
                If record has NO Bulk URI:
                    * NO Bulk URI + record_id + old_record + NO old_bulk_uri:           200 update

            * Bulk URI format invalid
            For given record:
                * data.ExtensionProperties is None
                * data.ExtensionProperties with no "wdms" field
                * data.ExtensionProperties["wdms"] with no bulkURI field
            For previous version record:
                * data with no "ExtensionProperties" field
                * data["ExtensionProperties"] with no "wdms" field
                * data["ExtensionProperties"]["wdms"] with no bulkURI field
    """

    # Mock init
    create_update_records_obj = CreateUpdateRecordsResponse(record_count=1, record_ids=["1"], skipped_record_ids=["1"])
    moc_get_record_not_found_error = mock.AsyncMock(
        side_effect=UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND,
                                       reason_phrase="", content=None, headers=None))
    moc_old_version_record_with_bulk_uri = _moc_get_record_previous_version({'name': 'myWell', 'uwi': '00-000-00000-00', 'ExtensionProperties': {'wdms': {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81'}}},
                                                record_id, record_kind)
    moc_old_version_record_without_wdms_field = _moc_get_record_previous_version({'name': 'myWell', 'uwi': '00-000-00000-00', 'ExtensionProperties': {}},
                                                record_id, record_kind)
    moc_old_version_record_without_ExtensionProperties_field = _moc_get_record_previous_version({'name': 'myWell', 'uwi': '00-000-00000-00'},
                                                record_id, record_kind)
    moc_old_version_record_without_bulk_uri_field = _moc_get_record_previous_version({'name': 'myWell', 'uwi': '00-000-00000-00', 'ExtensionProperties': {'wdms': {}}},
                                                record_id, record_kind)

    moc_create_or_update_records = mock.AsyncMock(return_value=create_update_records_obj)

    '''
         With mock returning NO previous version record:
                        If record has NO Bulk URI:
                            * NO Bulk URI + NO record_id :                          200 create
                            * NO Bulk URI + record_id + NO old_record :             200 create
                        If record has Bulk URI:
                            * Bulk URI + NO record_id :                             400 Err
                            * Bulk URI + record_id + NO old_record :                400 Err
    '''
    with mock.patch.object(StorageRecordServiceClientMock, "get_record", moc_get_record_not_found_error), \
         mock.patch.object(StorageRecordServiceClientMock, "create_or_update_records", moc_create_or_update_records):
        response_details = {"code": status.HTTP_200_OK, "message": None}

        # NO Bulk URI and NO record_id
        _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url, record_id=None,
                                                    record_kind=record_kind, data=data,
                                                    response_details=response_details)

        # NO Bulk URI, record_id and NO old_record
        _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                    record_id=record_id, record_kind=record_kind, data=data,
                                                    response_details=response_details)

        # Bulk URI set
        data_test = {
            "ExtensionProperties": {"wdms": {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236cca00'}}}

        # Bulk URI and NO record_id
        data_test.update(data)
        response_details = {"code": status.HTTP_400_BAD_REQUEST,
                            "message": '{"detail":"Record[0] error : no Bulk URI can be specified without record id"}'}
        _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url, record_id=None,
                                                    record_kind=record_kind,
                                                    data=data_test, response_details=response_details)

        # Bulk URI, record_id and NO old_record
        data_test.update(data)
        response_details = {"code": status.HTTP_400_BAD_REQUEST,
                            "message": '{"detail":"Record[0] error : no Bulk URI can be specified, given record_id has no ' \
                                       'previous version"}'}
        _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                    record_id=record_id,
                                                    record_kind=record_kind,
                                                    data=data_test, response_details=response_details)

        '''
            With mock returning previous version record with bulk URI:
                If record has NO Bulk URI:
                    * NO Bulk URI + record_id + old_record + old_bulk_uri:                              400 Err
                If record has Bulk URI:
                    * Bulk URI + record_id + old_record + old_bulk_uri + NO matching Bulk URI:          400 Err
                    * Bulk URI + record_id + old_record + old_bulk_uri + matching Bulk URI:             200 update
        '''
        with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                               mock.AsyncMock(return_value=moc_old_version_record_with_bulk_uri)):
            # NO Bulk URI, record_id, old_record and old_bulk_uri
            response_details = {"code": status.HTTP_400_BAD_REQUEST,
                                "message": '{"detail":"Record[0] error : Bulk URI isn\'t matching with the previous version one"}'}
            _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                        record_id=record_id,
                                                        record_kind=record_kind,
                                                        data=data, response_details=response_details)

            # Bulk URI, record_id, old_record, old_bulk_uri and NO matching Bulk URI
            response_details = {"code": status.HTTP_400_BAD_REQUEST,
                                "message": '{"detail":"Record[0] error : Bulk URI isn\'t matching with the previous version one"}'}
            _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                        record_id=record_id,
                                                        record_kind=record_kind,
                                                        data=data_test, response_details=response_details)

            # Bulk URI, record_id, old_record, old_bulk_uri and matching Bulk URI
            data_test = {
                "ExtensionProperties": {"wdms": {'bulkURI': 'urn:wdms-1:uuid:31fbda07-c414-4466-96d4-73a2236bba81'}}}
            data_test.update(data)
            response_details = {"code": status.HTTP_200_OK, "message": None}
            _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                        record_id=record_id,
                                                        record_kind=record_kind,
                                                        data=data_test, response_details=response_details)

            '''         
                 With mock returning previous version record without bulk URI:
                    If record has Bulk URI:
                        * Bulk URI + record_id + old_record + NO old_bulk_uri:              400 Err
                    If record has NO Bulk URI:
                        * NO Bulk URI + record_id + old_record + NO old_bulk_uri:           200 update
            '''
            with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                                   mock.AsyncMock(return_value=moc_old_version_record_without_bulk_uri_field)):
                # Bulk URI, record_id, old_record and NO old_bulk_uri
                response_details = {"code": status.HTTP_400_BAD_REQUEST,
                                    "message": '{"detail":"Record[0] error : no Bulk URI can be specified, given record_id has no bulkURI in its previous version"}'}
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id,
                                                            record_kind=record_kind,
                                                            data=data_test, response_details=response_details)

                # NO Bulk URI, record_id, old_record and NO old_bulk_uri
                response_details = {"code": status.HTTP_200_OK, "message": None}
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id,
                                                            record_kind=record_kind,
                                                            data=data, response_details=response_details)

                '''
                    * Bulk URI format invalid
                    For given record:
                        * data.ExtensionProperties is None
                        * data.ExtensionProperties with NO "wdms" field
                        * data.ExtensionProperties["wdms"] with NO bulkURI field
                '''

                # Bulk URI format invalid
                data_test = {"ExtensionProperties": {"wdms": {'bulkURI': 'urn:wdms-uib1223ca00'}}}
                data_test.update(data)
                record_to_test = _records_for_invalid_bulk_uri_set_test(record_id=None, record_kind=record_kind,
                                                                        data=data_test)
                with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
                    dasked_test_app_with_mocked_core_service.post(f"{base_url}", json=[record_to_test])

                response_details = {"code": status.HTTP_200_OK, "message": None}

                # data.ExtensionProperties field is None
                data_test = {"ExtensionProperties": None}
                data_test.update(data)
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=None,
                                                            record_kind=record_kind, data=data_test,
                                                            response_details=response_details)

                # data.ExtensionProperties with no "wdms" field
                data_test = {"ExtensionProperties": {}}
                data_test.update(data)
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id, record_kind=record_kind,
                                                            data=data_test,
                                                            response_details=response_details)

                # data.ExtensionProperties["wdms"] with no bulkURI field
                data_test = {"ExtensionProperties": {"wdms": {}}}
                data_test.update(data)
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id, record_kind=record_kind,
                                                            data=data_test,
                                                            response_details=response_details)
            '''
                For previous version record:
                    * data with NO "ExtensionProperties" field
                    * data["ExtensionProperties"] with NO "wdms" field
                    * data["ExtensionProperties"]["wdms"] with NO bulkURI field (done above)
            '''
            with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                                   mock.AsyncMock(return_value=moc_old_version_record_without_ExtensionProperties_field)):
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id, record_kind=record_kind, data=data,
                                                            response_details=response_details)

            with mock.patch.object(StorageRecordServiceClientMock, "get_record",
                                   mock.AsyncMock(return_value=moc_old_version_record_without_wdms_field)):
                _assert_check_for_invalid_bulk_uri_set_test(dasked_test_app_with_mocked_core_service, base_url,
                                                            record_id=record_id, record_kind=record_kind, data=data,
                                                            response_details=response_details)
