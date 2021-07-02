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

import pytest
import mock
import json
import os

from fastapi.testclient import TestClient

from fastapi import Header, status

from odes_storage.models import CreateUpdateRecordsResponse, Record

from app.model.osdu_model import Wellbore, Well
from app.clients import SearchServiceClient, StorageRecordServiceClient

from app.helper import traces
from app.middleware import require_data_partition_id
from app.auth.auth import require_opendes_authorized_user
from app.utils import Context
from app.wdms_app import wdms_app, app_injector
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
            kind="namespace:osdu:Wellbore:2.7.112",
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
            kind="namespace:osdu:Wellbore:2.7.112",
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

    async def set_default_partition(data_partition_id: str = Header("opendes")):
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
        response = client.post(base_url, data=json.dumps(test_Wellbores), headers={'content-type' : 'application/json'})

        # then
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


getas_parameters = [
    (Wellbore, "/ddms/v3/wellbores", r"../../converter/wellbore_wks.json", "opendes:wellbore:12345"),
    (Wellbore, "/ddms/v3/wellbores",r"../../converter/wellbore_wks.json", "opendes:master-data--Wellbore:6f70656e6465733a646f633a3132333435:"),
    (Wellbore, "/ddms/v3/wellbores", r"../../../../app/model_examples/wellbore_v3.json", "opendes:master-data--Wellbore:123"),
    (Well, "/ddms/v3/wells", r"../../converter/well_wks.json", "opendes:well:12345"),
    (Well, "/ddms/v3/wells", r"../../converter/well_wks.json", "opendes:master-data--Well:6f70656e6465733a646f633a3132333435:"),
    (Well, "/ddms/v3/wells", r"../../../../app/model_examples/well_v3.json", "opendes:master-data--Well:12345:456"),
]


def replace_template(source_obj_str: str) -> str:
    source_obj_str = source_obj_str.replace("{{datapartitionid}}", "datapartitionid")\
        .replace("{datapartitionid}", "datapartitionid").replace("{{domain}}", "domain")\
        .replace("{{wellboreId}}", "wellboreId").replace("{{wellId}}", "wellId")
    return source_obj_str


@pytest.mark.parametrize("entity_class, base_url, source_file, record_id", getas_parameters)
def test_get_record_as_OSDU(client, entity_class, base_url, source_file, record_id):
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

        assert response.status_code == status.HTTP_200_OK

        # assert it validates the input object schema
        res = response.json()
        entity_class.validate(res)


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
