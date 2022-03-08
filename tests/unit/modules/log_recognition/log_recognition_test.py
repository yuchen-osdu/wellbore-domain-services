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

import time
import mock
import pytest

from fastapi import Header, status
from fastapi.testclient import TestClient
from odes_storage import models as m
from odes_storage.exceptions import UnexpectedResponse
from odes_storage.models import CreateUpdateRecordsResponse

from app.conf import ConfigurationContainer
from app.auth.auth import require_opendes_authorized_user
from app.clients import *
from app.helper import traces
from app.middleware import require_data_partition_id
from app.modules.log_recognition.routers.log_recognition import family_processor_manager
from app.utils import Context
from app.wdms_app import wdms_app, add_modules_routers, remove_modules_routers
from tests.unit.test_utils import create_mock_class

StorageRecordServiceClientMock = create_mock_class(StorageRecordServiceClient)
SearchServiceClientMock = create_mock_class(SearchServiceClient)


@pytest.fixture
def client():
    async def bypass_authorization():
        pass

    async def set_default_partition(data_partition_id: str = Header('opendes')):
        Context.set_current_with_value(partition_id=data_partition_id)

    mock_storage = mock.AsyncMock(return_value=StorageRecordServiceClientMock())
    with mock.patch('app.modules.log_recognition.routers.family_processor_manager.get_storage_record_service', mock_storage):
        with mock.patch('app.modules.log_recognition.routers.log_recognition.get_storage_record_service', mock_storage):
            # override authentication dependency
            previous_overrides = wdms_app.dependency_overrides

            try:
                wdms_app.dependency_overrides[require_opendes_authorized_user] = bypass_authorization
                wdms_app.dependency_overrides[require_data_partition_id] = set_default_partition
                client = TestClient(wdms_app)
                yield client
            finally:
                wdms_app.dependency_overrides = previous_overrides  # clean up


@pytest.fixture(autouse=True)
def setup_teardown():
    # setup
    # run the test
    yield
    # teardown
    family_processor_manager._processors["opendes"] = None
    family_processor_manager._catalog_lifetime = 200


# Initialize traces exporter in app, like it is in app's startup decorator
wdms_app.trace_exporter = traces.CombinedExporter(service_name='tested-ddms')


@pytest.mark.parametrize("label, unit, expected", [
    ('GR', 'gAPI', {'family': 'Gamma Ray', 'family_type': ['Gamma Ray'], 'log_unit': 'gAPI', 'base_unit': 'gAPI'}),
    ('TVD', 'cm', {'family': 'True Vertical Depth', 'family_type': ['Reference'], 'log_unit': 'cm', 'base_unit': 'ft'}),
    ('DTC', 'us/cm',
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'}),
    ('TRUESTRATIGRAPHICTHICKNESS1', 'ft',
     {"family": "Thickness", "family_type": ["Formation Geometry", "Rock Quality"], "log_unit": "ft", "base_unit": "ft"})
])
def test_family_assignment_rules(client, label, unit, expected):
    with StorageRecordServiceClientMock.set_throw(
            'get_record',
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)):
        response = client.post("/log-recognition/family",
                               json={"label": label,
                                     "log_unit": unit})
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert response_json == expected


def test_family_assignment_rules_not_found(client):
    with StorageRecordServiceClientMock.set_throw(
            'get_record',
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)):
        response = client.post("/log-recognition/family",
                               json={"label": "unknown",
                                     "log_unit": ""})
        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_good_catalog(client):
    good_catalog = {
        "data": {
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}],
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        "legal": {
            "legaltags": [
                "opendes-public-usa-dataset-1"
            ],
            "otherRelevantDataCountries": [
                "US"
            ],
            "status": "compliant"
        },
        "acl": {
            "viewers": [
                "data.default.viewers@opendes.p4d.cloud.slb-ds.com"
            ],
            "owners": [
                "data.default.owners@opendes.p4d.cloud.slb-ds.com"
            ]
        }
    }

    expected_response = CreateUpdateRecordsResponse(recordCount=1, recordIds=['rec1'])
    moc_create_or_update_records = mock.AsyncMock(return_value=expected_response)

    with mock.patch.object(StorageRecordServiceClientMock, 'create_or_update_records', moc_create_or_update_records):
        response = client.put("/log-recognition/upload-catalog", json=good_catalog)
        assert response.status_code == status.HTTP_200_OK
        assert CreateUpdateRecordsResponse.parse_raw(response.text) == expected_response


@pytest.mark.parametrize("label, unit, code, expected", [
    ('fantomas', '', status.HTTP_404_NOT_FOUND, {}),
    ('FF', 'f', status.HTTP_200_OK,
     {'family': 'fake family', 'family_type': ['Fake'], 'log_unit': 'f', 'base_unit': 'ef'}),
    ('OF', 'g', status.HTTP_200_OK,
     {'family': 'other fake family', 'family_type': ['Other Fake'], 'log_unit': 'g', 'base_unit': 'jai'}),
    ('AOF', 'gg', status.HTTP_200_OK,
     {'family': "another fake family", 'family_type': ["Other Fake", "Another fake family"],
      'log_unit': 'gg', 'base_unit': 'jaijai'}),
    ('DTC', 'us/cm', status.HTTP_200_OK,
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'})
])
def test_family_assignment_rules_custom(client, label, unit, code, expected):
    record_obj = m.Record(
        data={
            "family_catalog": [
                {"unit": "f", "family": "fake family", "rule": "FF"},
                {"unit": "g", "family": "other fake family", "rule": "OF"},
                {"unit": "gg", "family": "another fake family", "rule": "AOF"}
            ],
            "main_family_catalog": [
                {"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"},
                {"MainFamily": ["Other Fake", "Another fake family"], "Family": "another fake family", "Unit": "jaijai"}
            ]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    moc_storage = mock.AsyncMock(return_value=record_obj)

    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_storage):
        response = client.post("/log-recognition/family",
                               json={"label": label,
                                     "log_unit": unit})

        assert response.status_code == code
        if code == status.HTTP_200_OK:
            response_json = response.json()
            assert response_json == expected


@pytest.mark.parametrize("label, unit, code, expected", [
    ('OF', 'F', status.HTTP_404_NOT_FOUND, {}),
    ('DTC', 'us/cm', status.HTTP_200_OK,
     {'family': 'Compressional Slowness', 'family_type': ['Slowness'], 'log_unit': 'us/cm', 'base_unit': 'us/ft'})
])
def test_family_assignment_rules_custom_catalog_not_found(client, label, unit, code, expected):
    with StorageRecordServiceClientMock.set_throw(
            'get_record',
            UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase="", content=None, headers=None)):
        response = client.post("/log-recognition/family",
                               json={"label": label,
                                     "log_unit": unit})

        assert response.status_code == code
        if code == status.HTTP_200_OK:
            response_json = response.json()
            assert response_json == expected


def test_failing_storage(client):
    unexpected_response = UnexpectedResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                             reason_phrase="", content=b'content', headers=None)

    with StorageRecordServiceClientMock.set_throw('get_record', unexpected_response):
        response = client.post("/log-recognition/family",
                               json={"label": "MD",
                                     "log_unit": "M"})

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_unvalidate_catalogs(client):
    record_obj = m.Record(
        data={
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}],
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    moc_storage = mock.AsyncMock(return_value=record_obj)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_storage):
        # Force a big catalog_lifetime
        family_processor_manager._catalog_lifetime = 1000

        moc_storage.assert_not_called()
        response = client.post("/log-recognition/family",
                               json={"label": "FF",
                                     "log_unit": "f"})
        assert response.status_code == status.HTTP_200_OK
        assert moc_storage.call_count == 1

        response = client.post("/log-recognition/family",
                               json={"label": "FF",
                                     "log_unit": "f"})
        assert response.status_code == status.HTTP_200_OK
        assert moc_storage.call_count == 1

        # Force a small catalog_lifetime
        family_processor_manager._catalog_lifetime = 1
        # Sorry we need to sleep 1 second
        time.sleep(1)
        response = client.post("/log-recognition/family",
                               json={"label": "FF",
                                     "log_unit": "f"})
        assert response.status_code == status.HTTP_200_OK
        assert moc_storage.call_count == 2

        time.sleep(1)
        response = client.post("/log-recognition/family",
                               json={"label": "FF",
                                     "log_unit": "f"})
        assert response.status_code == status.HTTP_200_OK
        assert moc_storage.call_count == 3


nb_storage_call = 0


def test_invalidate_default_catalogs(client):
    def response_fn(*args, **kwargs):
        global nb_storage_call
        nb_storage_call += 1
        raise UnexpectedResponse(status_code=status.HTTP_404_NOT_FOUND, reason_phrase='', content=b'', headers=None)

    with StorageRecordServiceClientMock.set_answer('get_record', response_fn):
        global nb_storage_call
        response = client.post("/log-recognition/family",
                               json={"label": "GR",
                                     "log_unit": "gApi"})
        assert response.status_code == status.HTTP_200_OK
        assert nb_storage_call == 1

        response = client.post("/log-recognition/family",
                               json={"label": "GR",
                                     "log_unit": "gApi"})
        assert response.status_code == status.HTTP_200_OK
        assert nb_storage_call == 1  # we are inside the catalog_lifetime so no call to DE

        family_processor_manager._catalog_lifetime = 1
        time.sleep(1)
        response = client.post("/log-recognition/family",
                               json={"label": "GR",
                                     "log_unit": "gApi"})
        assert response.status_code == status.HTTP_200_OK
        assert nb_storage_call == 2  # catalog_lifetime excedeed, one more call to DE expected


def test_no_catalog(client):
    record_obj = m.Record(
        data={
            "main_family_catalog": [{"MainFamily": "Fake", "Family": "fake family", "Unit": "ef"},
                                    {"MainFamily": "Other Fake", "Family": "other fake family", "Unit": "jai"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    moc_storage = mock.AsyncMock(return_value=record_obj)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_storage):
        response = client.post("/log-recognition/family",
                               json={"label": "MD",
                                     "log_unit": "m"})
        assert response.status_code == status.HTTP_200_OK


def test_no_main_family_catalog(client):
    record_obj = m.Record(
        data={
            "family_catalog": [{"unit": "f", "family": "fake family", "rule": "FF"},
                               {"unit": "g", "family": "other fake family", "rule": "OF"}]
        },
        kind="",
        acl=m.StorageAcl(viewers=[], owners=[]),
        legal={}
    )

    moc_storage = mock.AsyncMock(return_value=record_obj)
    with mock.patch.object(StorageRecordServiceClientMock, 'get_record', moc_storage):
        response = client.post("/log-recognition/family",
                               json={"label": "OF",
                                     "log_unit": "g"})
        assert response.status_code == status.HTTP_200_OK
        response_json = response.json()
        assert response_json == {"family": "other fake family", "family_type": None, "log_unit": "g", "base_unit": None}


def test_swagger_generation():
    swagger_dict = wdms_app.openapi()
    assert swagger_dict["paths"].get("/log-recognition/family", None) is not None
    assert swagger_dict["paths"]["/log-recognition/family"]["post"]["summary"] == 'Recognize family and unit'
    assert swagger_dict["paths"]["/log-recognition/family"]["post"][
               "description"] == 'Find the most probable family and ' \
                                 'unit using family assignment rule based catalogs. User defined catalog will have the priority.'
    assert \
        swagger_dict["paths"]["/log-recognition/family"]["post"]["requestBody"]["content"]["application/json"][
            "schema"][
            "$ref"] == '#/components/schemas/GuessRequest'
    assert swagger_dict["components"]["schemas"]["GuessRequest"]["example"] == {'label': 'GRD', 'log_unit': 'GAPI',
                                                                                'description': 'LDTD Gamma Ray'}

    assert swagger_dict["paths"].get("/log-recognition/upload-catalog", None) is not None
    assert swagger_dict["paths"]["/log-recognition/upload-catalog"]["put"][
               "summary"] == 'Upload user-defined catalog with family assignment rules'
    assert swagger_dict["paths"]["/log-recognition/upload-catalog"]["put"]["description"] == """Upload user-defined catalog with family assignment rules for specific partition ID. 
            If there is an existing catalog, it will be replaced. It takes maximum of 5 mins to replace the existing catalog. 
            Hence, any call to retrieve the family should be made after 5 mins of uploading the catalog. <p>Required roles: 'users.datalake.editors' or 'users.datalake.admins'.</p>"""
    assert \
        swagger_dict["paths"]["/log-recognition/upload-catalog"]["put"]["requestBody"]["content"]["application/json"][
            "schema"][
            "$ref"] == '#/components/schemas/CatalogRecord'
    assert swagger_dict["components"]["schemas"]["CatalogRecord"]["example"] == {
        'acl': {'viewers': ['abc@domain.com, cde@domain.com'], 'owners': ['abc@domain.com, cde@domain.com']},
        'legal': {'legaltags': ['opendes-public-usa-dataset-1'], 'otherRelevantDataCountries': ['US']},
        'data': {'family_catalog': [{'unit': 'ohm.m', 'family': 'Medium Resistivity', 'rule': 'MEDR'}],
                 'main_family_catalog': [
                     {'MainFamily': 'Resistivity', 'Family': 'Medium Resistivity', 'Unit': 'OHMM'}]}}

    assert swagger_dict is not None


# Global module setup / teardown
def setup_module(nope_logger_fixture):
    ConfigurationContainer.modules.value = "log_recognition.routers.log_recognition"
    add_modules_routers()

def teardown_module():
    remove_modules_routers()

