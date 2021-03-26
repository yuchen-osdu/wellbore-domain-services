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
from app.model.osdu_model import Wellbore
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

modules_to_patch = [f"app.routers.ddms_v3.{m}" for m in ["wellbore_ddms_v3"]]

tests_parameters = [
    (
        "/ddms/v3/wellbores",
        Wellbore(
            id=r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
            kind="namespace:osdu:Wellbore:2.7.112",
            groupType="master-data",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
            },
            data={},
        ),
        Record(
            id=r"namespace:master-data--Wellbore:c7c421a7-f496-5aef-8093-298c32bfdea9",
            kind="namespace:osdu:Wellbore:2.7.112",
            groupType="master-data",
            acl={"owners": ["me@osdu.org"], "viewers": ["ze@osdu.org"]},
            legal={
                "legaltags": ["string"],
                "otherRelevantDataCountries": ["FR"],
                "status": r"compliant",
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
        wdms_app.dependency_overrides[
            require_data_partition_id
        ] = set_default_partition
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

    moc_create_or_update_records = mock.AsyncMock(
        return_value=expected_response
    )

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
        response = client.post(base_url, data=json.dumps(test_Wellbores))

        # then
        assert response.status_code == status.HTTP_200_OK
        assert (
            CreateUpdateRecordsResponse.parse_raw(response.text)
            == expected_response
        )
